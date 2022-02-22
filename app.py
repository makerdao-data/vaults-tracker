#  Copyright 2021 DAI Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from flask import Flask, request, render_template, jsonify, Response
from datetime import datetime
import atexit
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from sqlalchemy.dialects import registry
from io import StringIO
import csv
from flask import make_response, send_file

import os

from config import SECRET
from connectors.sf import sf, sf_disconnect
from views.main_view import main_page_view, main_page_data
from views.vault_view import vault_page_view, vault_page_data
from views.collateral_view import collateral_page_view, collateral_page_data
from views.owner_view import owner_page_view, owner_page_data
from views.history_view import history_page_view
from views.daily_history_view import daily_history_page_view

registry.register("snowflake", "snowflake.sqlalchemy", "dialect")

app = Flask(__name__)
app.secret_key = SECRET
app.config["JSON_SORT_KEYS"] = False
app.config["DEBUG"] = True
csrf = CSRFProtect(app)

connect_url = sqlalchemy.engine.url.URL(
    "snowflake",
    username=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASS"),
    host=os.getenv("SNOWFLAKE_ACCOUNT"),
    query={
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "role": os.getenv("SNOWFLAKE_ROLE"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    },
)

app.config['SQLALCHEMY_DATABASE_URI'] = connect_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

SELF = "'self'"
UNSAFE_INLINE = "'unsafe-inline'"
UNSAFE_EVAL = "'unsafe-eval'"
talisman = Talisman(
    app,
    force_https=False,
    content_security_policy={
        "default-src": [SELF],
        "img-src": ["*", "data:"],
        "script-src": [
            SELF,
            UNSAFE_EVAL,
            UNSAFE_INLINE,
            "https://cdn.plot.ly/",
            "https://cdn.datatables.net/",
            "https://cdnjs.cloudflare.com/",
            "https://code.jquery.com/",
            "https://cdn.jsdelivr.net/",
            "https://cdn.datatables.net/"

        ],
        "style-src": [
            SELF,
            UNSAFE_INLINE,
            "https://cdn.datatables.net/",
            "https://cdnjs.cloudflare.com/",
            "https://cdn.jsdelivr.net",
            "https://code.jquery.com/"
        ],
        "font-src": [SELF, "https://cdnjs.cloudflare.com/"],
    },
    content_security_policy_nonce_in=["script-src"],
    feature_policy={"geolocation": "'none'"},
)

class History(db.Model):

    __tablename__ = 'vaults'

    day = db.Column(db.DateTime)
    vault = db.Column(db.String)
    ilk = db.Column(db.String)
    collateral_eod = db.Column(db.Float)
    principal_eod = db.Column(db.Float)
    debt_eod = db.Column(db.Float)
    fees_eod = db.Column(db.Float)
    withdraw = db.Column(db.Float)
    deposit = db.Column(db.Float)
    principal_generate = db.Column(db.Float)
    principal_payback = db.Column(db.Float)
    debt_generate = db.Column(db.Float)
    debt_payback = db.Column(db.Float)
    fees = db.Column(db.Float)

    def to_dict(self):
        return {
            'day' : self.day,
            'vault' : self.vault, 
            'ilk' : self.ilk,
            'collateral_eod' : self.collateral_eod,
            'principal_eod' : self.principal_eod,
            'debt_eod' : self.debt_eod,
            'fees_eod' : self.fees_eod,
            'withdraw' : self.withdraw,
            'deposit' : self.deposit,
            'principal_generate' : self.principal_generate,
            'principal_payback' : self.principal_payback,
            'debt_generate' : self.debt_generate,
            'debt_payback' : self.debt_payback,
            'fees' : self.fees,
        }
    
    def to_list(self):
        return [
            self.day,
            self.vault, 
            self.ilk,
            self.collateral_eod,
            self.principal_eod,
            self.debt_eod,
            self.fees_eod,
            self.withdraw,
            self.deposit,
            self.principal_generate,
            self.principal_payback,
            self.debt_generate,
            self.debt_payback,
            self.fees
        ]
    
    __table_args__ = {"schema": "maker.history"}
    __mapper_args__ = {
        "primary_key": [
            day,
            vault,
            ilk
        ]
    }

db.create_all()


# HTML endpoints -------------------------------------------


@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", title="404"), 404


@app.errorhandler(500)
def page_not_found(error):
    return render_template("500.html", title="500"), 500


@app.route("/", methods=["GET", "POST"])
def main_page():
    return main_page_view(sf)


@app.route("/vault/<vault_id>", methods=["GET", "POST"])
def vault_page(vault_id):
    return vault_page_view(sf, vault_id)


@app.route("/collateral/<collateral_id>", methods=["GET", "POST"])
def collateral_page(collateral_id):
    return collateral_page_view(sf, collateral_id.upper())


@app.route("/owner/<owner_id>", methods=["GET", "POST"])
def owner_page(owner_id):
    return owner_page_view(sf, owner_id.lower())


@app.route("/tos")
def tos_page():
    return render_template("tos.html", refresh=datetime.utcnow())


@app.route("/history")
def history_page():
    return history_page_view(sf)


@app.route("/daily_history")
def daily_history_page():
    print(request.args)
    return daily_history_page_view(sf)


# DATA endpoints -------------------------------------------


@app.route("/data/main", methods=["GET"])
def get_main_page_data():
    dataset = main_page_data(sf)
    return jsonify(dataset)


@app.route("/data/vault/<vault_id>", methods=["GET"])
def get_vault_page_data(vault_id):
    dataset = vault_page_data(sf, vault_id)
    return jsonify(dataset)


@app.route("/data/collateral/<collateral_id>", methods=["GET"])
def get_collateral_page_data(collateral_id):
    dataset = collateral_page_data(sf, collateral_id)
    return jsonify(dataset)


@app.route("/data/owner/<owner_id>", methods=["GET"])
def get_owner_page_data(owner_id):
    dataset = owner_page_data(sf, owner_id)
    return jsonify(dataset)


@app.route("/data/history/<date>", methods=["GET"])
def data(date):

    query = History.query
    query = query.filter(History.day == date)

    # search filter
    search = request.args.get('search[value]')
    if search:

        query = query.filter(db.or_(
            History.vault.like(f'%{search}%'),
            History.ilk.like(f'%{search}%')
        ))

    total_filtered = query.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        if col_name not in ['day', 'vault', 'ilk', 'collateral_eod', 'principal_eod', 'debt_eod', 'fees_eod']:
            col_name = 'day'
        descending = request.args.get(f'order[{i}][dir]') == 'desc'
        col = getattr(History, col_name)
        if descending:
            col = col.desc()
        order.append(col)
        i += 1
    if order:
        query = query.order_by(*order)

    # pagination
    start = request.args.get('start', type=int)
    length = request.args.get('length', type=int)
    query = query.offset(start).limit(length)

    # response
    return {
        'data': [record.to_dict() for record in query],
        'recordsFiltered': total_filtered,
        'recordsTotal': History.query.count(),
        'draw': request.args.get('draw', type=int),
    }


@app.route("/data/history_export/<date>", methods=["GET"])
def history_export(date):

    query = History.query
    query = query.filter(History.day == date)

    csv = 'day,vault, ilk,collateral_eod,principal_eod,debt_eod,fees_eod,withdraw,deposit,principal_generate,principal_payback,debt_generate,debt_payback,fees\n'

    for i in query:
        for j in i.to_list():
            csv += (str(j) + ',')

        csv = csv[:-1] + '\n'

    response = make_response(csv)
    response.headers['Content-Disposition'] = 'attachment; filename=export.csv'
    response.mimetype='text/csv'

    return response



# cleanup tasks
def cleanup_task():
    if not sf.is_closed():
        sf_disconnect(sf)
        print("SF connection closed.")


atexit.register(cleanup_task)


if __name__ == "__main__":
    app.run(debug=True)
