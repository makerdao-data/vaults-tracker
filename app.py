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
from typing import Generator
from datetime import datetime
import atexit
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import registry
import csv
from io import StringIO
from werkzeug.wrappers import Response

from config import SECRET, connect_url
from connectors.sf import sf, sf_disconnect
from models.history import History
from views.main_view import main_page_view, main_page_data
from views.vault_view import vault_page_view, vault_page_data
from views.collateral_view import collateral_page_view, collateral_page_data
from views.owner_view import owner_page_view, owner_page_data
from views.history_view import history_page_view

from deps import get_db

registry.register("snowflake", "snowflake.sqlalchemy", "dialect")

app = Flask(__name__)
app.secret_key = SECRET
app.config["JSON_SORT_KEYS"] = False
app.config["DEBUG"] = True
csrf = CSRFProtect(app)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database import Base, engine, SessionLocal
from config import connect_url
from models import History


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


@app.route("/history", methods=["GET", "POST"])
def history_page():
    return history_page_view(sf)


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


@app.route("/data/history/<s>/<e>", methods=["GET", "POST"])
def data(s, e):

    s = datetime.fromtimestamp(int(s)/1000).__str__()[:10]
    e = datetime.fromtimestamp(int(e)/1000).__str__()[:10]

    session = next(get_db())

    query = session.query(History)
    query = query.filter(History.day >= s).filter(History.day <= e)

    vault = request.args.get('search_vault')
    if vault:
        query = query.filter(
            History.vault == str(vault)
        )
    
    ilk = request.args.get('search_ilk')
    if ilk:
        query = query.filter(
            History.ilk == str(ilk)
        )

    total_filtered = query.count()

    # sorting
    order = []
    i = 0
    while True:
        col_index = request.args.get(f'order[{i}][column]')
        if col_index is None:
            break
        col_name = request.args.get(f'columns[{col_index}][data]')
        if col_name not in [
            'day', 'vault', 'ilk',
            'collateral_eod', 'principal_eod', 'debt_eod', 'fees_eod',
            'withdraw', 'deposit',
            'principal_generate', 'principal_payback',
            'debt_generate', 'debt_payback',
            'accrued_fees'
        ]:
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

    records_total = session.query(History).count()

    # response
    return {
        'data': [record.to_dict() for record in query],
        'recordsFiltered': total_filtered,
        'recordsTotal': records_total,
        'draw': request.args.get('draw', type=int),
    }


@app.route("/data/history_export/<s>/<e>", methods=["GET"])
def history_export(s, e):


    s = datetime.fromtimestamp(int(s)/1000).__str__()[:10]
    e = datetime.fromtimestamp(int(e)/1000).__str__()[:10]

    session = next(get_db())

    query = session.query(History)
    query = query.filter(History.day >= s).filter(History.day <= e)

    vault = request.args.get('search_vault')
    if vault:
        query = query.filter(
            History.vault == str(vault)
        )
    
    ilk = request.args.get('search_ilk')
    if ilk:
        query = query.filter(
            History.ilk == str(ilk)
        )

    def generate():

        data = StringIO()
        w = csv.writer(data)

        # write header
        w.writerow(('day','vault', 'ilk','collateral_eod','principal_eod','debt_eod','fees_eod','withdraw','deposit','principal_generate','principal_payback','debt_generate','debt_payback','fees'))
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)

        # write each log item
        for item in query:
            w.writerow(tuple(item.to_list()))
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    # stream the response as the data is generated
    response = Response(generate(), mimetype='text/csv')
    # add a filename
    response.headers.set("Content-Disposition", "attachment", filename="export.csv")
    return response

# cleanup tasks
def cleanup_task():
    if not sf.is_closed():
        sf_disconnect(sf)
        print("SF connection closed.")


atexit.register(cleanup_task)


if __name__ == "__main__":
    app.run(debug=True)
