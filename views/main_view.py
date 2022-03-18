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

import json
from json.tool import main
from flask import render_template, request
from datetime import datetime

from config import ACTIVE_DUST_LIMIT, STABLECOINS
from connectors.sf import sf_connect
from utils.utils import async_queries, get_last_refresh
from utils.tables import link
from utils.vat import get_vat_data

from forms.forms import SearchForm
from utils.searchbar import run_search
from graphs.collateralization import main_collateralization_graph
from graphs.pie import main_pie, main_sunburst
from graphs.bar import main_bar
import plotly.express as px

from datetime import datetime


def main_page_data(sf):
    # test snowflake connection and reconnect if necessary
    try:
        if sf.is_closed():
            sf = sf_connect()
        if sf.is_closed():
            raise Exception("Reconnection failed")

    except Exception as e:
        print(e)
        return dict(status="failure", data="Database connection error")

    try:
        result = async_queries(sf, [
            dict(query="SELECT * FROM MCD.TRACKERS.vault_TRACKER",
                 id="vault_tracker")
        ])['vault_tracker'][0]

        return dict(status="success",
                    data=dict(
                        total_debt=result[0],
                        collaterals=json.loads(result[1])['data'],
                        collaterals_num=result[2],
                        vaults_num=result[3],
                        active_num=result[4],
                        debt_ceiling=result[5],
                        debt_utilization=result[6],
                        available_debt=result[7],
                        available_collateral=result[8],
                        owners=result[9],
                        active_owners=result[10],
                        collateralization=result[11],
                        locked_value=result[12],
                        refresh=result[13],
                        sin=result[14],
                        pie=json.dumps(json.loads(result[15])),
                        bar=json.dumps(json.loads(result[16])),
                    ))

    except Exception as e:
        print(e)
        return dict(status="failure", data="Backend error: %s" % e)


# flask view for the main page
def main_page_view(sf):

    try:
        plot = main_collateralization_graph([], [])

        block, last_time = get_last_refresh(sf)

        search = SearchForm(request.form)
        if request.method == "POST":
            return run_search(search.data["search"])

        return render_template(
            "main.html",
            plot=plot,
            refresh="{0:,.0f}".format(block) + " / " + str(last_time),
            form=search,
        )

    except Exception as e:
        print(e)
        return render_template("error.html", error_message=str(e))
