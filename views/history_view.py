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

import os
from flask import render_template, request
from connectors.sf import sf_connect
from utils.utils import get_last_refresh

from forms.forms import SearchForm
from utils.searchbar import run_search

def history_page_view(sf):

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

        block, last_time = get_last_refresh(sf)

        search = SearchForm(request.form)
        if request.method == "POST":
            return run_search(search.data["search"])

        return render_template(
            "vaults_history.html",
            refresh="{0:,.0f}".format(block) + " / " + str(last_time),
            form=search,
        )

    except Exception as e:
        print(e)
        return render_template("error.html", error_message=str(e))