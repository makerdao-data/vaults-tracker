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

        # list of available collaterals
        ilks_query = "SELECT ilk FROM internal.ilks; "

        # current vaults list
        vaults_query = """
            SELECT
                vault,
                ilk,
                collateral,
                debt,
                available_debt,
                available_collateral,
                owner,
                collateralization, 
                osm_price 
            FROM mcd.public.current_vaults;
            """
        
        pie_query = """
            select
            case
            when SPLIT_PART(v.ilk, '-', 0) = 'PSM' then 'STABLE'
            when i.type = 'lp' then 'NON-STABLE'
            when v.ilk like 'GUNIV3%' then 'STABLE'
            when i.type = 'stablecoin' then 'STABLE'
            when i.type = 'coin' then 'NON-STABLE'
            when SPLIT_PART(v.ilk, '-', 0) = 'DIRECT' then 'NON-STABLE'
            when i.type = 'None' then 'NON-STABLE'
            else upper(i.type)
            end type,
            sum( v.collateral * v.osm_price ) value_locked
            from mcd.public.current_vaults v
            join mcd.internal.ilks i
            on v.ilk = i.ilk
            where v.ilk != 'SAI'
            group by i.type, v.ilk;
        """

        bar_query = """
            select type, case when type = 'RWA' then null else sum(value_locked) end VALUE_LOCKED, sum(debt)
            from (
            select
            case
            when SPLIT_PART(v.ilk, '-', 0) = 'PSM' then 'PSM'
            when v.ilk like 'RWA0%' then 'RWA'
            when SPLIT_PART(v.ilk, '-', 0) = 'DIRECT' then 'D3M'
            when v.ilk like 'GUNIV3%' then 'G-UNI'
            else upper('REGULAR VAULT')
            end type,
            v.ilk,
            sum( v.collateral * v.osm_price ) value_locked, sum( v.debt ) debt
            from mcd.public.current_vaults v
            join mcd.internal.ilks i
            on v.ilk = i.ilk
            group by i.type, v.ilk
            )
            where debt > 0
            group by type;
        """

        sin_query = """
            select sin
            from mcd.internal.vow
            order by timestamp desc
            limit 1;
        """

        all_queries = [
            dict(query=vaults_query, id="vaults"),
            dict(query=ilks_query, id="ilks"),
            dict(query=pie_query, id="pie"),
            dict(query=bar_query, id="bar"),
            dict(query=sin_query, id="sin")
        ]

        sf_responses = async_queries(sf, all_queries)
        vaults = sf_responses["vaults"]
        ilks = sf_responses["ilks"]
        pie_data = sf_responses["pie"]
        bar_data = sf_responses["bar"]
        sin = sf_responses["sin"]
        sin = sin[0][0]

        # data processing

        collaterals = dict()
        for m in ilks:
            collaterals[m[0]] = dict()

        Line = get_vat_data()

        owners = set()
        active_owners = set()

        for c in collaterals:
            collaterals[c]["debt"] = 0
            collaterals[c]["locked_amount"] = 0
            collaterals[c]["available_debt"] = 0
            collaterals[c]["available_collateral"] = 0
            collaterals[c]["available_collateral_usd"] = 0
            collaterals[c]["vaults_num"] = 0
            collaterals[c]["active_num"] = 0
            collaterals[c]["osm_price"] = 0

        # coll_buckets = {}
        # coll_buckets_stable = {}

        # iterate over all vaults

        for vault in vaults:

            # build sets of owners and active owners
            owners.add(vault[6])
            if vault[3] > ACTIVE_DUST_LIMIT:
                active_owners.add(vault[6])

            # # build collateralization buckets
            # if vault[7]:
            #     bucket = min(round(vault[7]), 1000)
            #     if vault[1].split("-")[0] in STABLECOINS:

            #         if bucket not in coll_buckets_stable:
            #             coll_buckets_stable[bucket] = 0

            #         coll_buckets_stable[bucket] += vault[3]

            #     else:

            #         if bucket not in coll_buckets:
            #             coll_buckets[bucket] = 0

            #         coll_buckets[bucket] += vault[3]

            # aggregate collaterals info
            collaterals[vault[1]]["vaults_num"] += 1
            collaterals[vault[1]]["active_num"] += 1 if vault[3] > 20 else 0
            collaterals[vault[1]]["locked_amount"] += vault[2]
            collaterals[vault[1]]["debt"] += vault[3]
            collaterals[vault[1]]["available_debt"] += vault[4] or 0
            collaterals[vault[1]]["available_collateral"] += vault[5]
            if vault[8]:
                collaterals[vault[1]]["osm_price"] = vault[8]
            collaterals[vault[1]]["available_collateral_usd"] += (
                vault[5] * collaterals[vault[1]]["osm_price"]
            )

        # add additional information
        for c in collaterals:
            collaterals[c]["locked_value"] = (
                collaterals[c]["locked_amount"] * collaterals[c]["osm_price"]
            )
            collaterals[c]["collateralization"] = (
                (collaterals[c]["locked_value"] / collaterals[c]["debt"])
                if collaterals[c]["locked_value"]
                and collaterals[c]["debt"]
                and collaterals[c]["debt"] > 1e-10
                else None
            )

        collaterals_list = [
            [
                collateral,
                c["active_num"],
                c["vaults_num"],
                c["locked_value"],
                c["debt"],
                c["available_debt"],
                c["available_collateral"],
                c["available_collateral_usd"],
                c["collateralization"],
                c["osm_price"],
            ]
            for collateral, c in collaterals.items()
        ]
        collaterals_list.sort(key=lambda _c: _c[4], reverse=True)

        # calculate total stats
        vaults_num = sum([c[2] for c in collaterals_list])
        active_num = sum([c[1] for c in collaterals_list])
        locked_value = sum([c[3] for c in collaterals_list])
        total_debt = sum([c[4] for c in collaterals_list])
        available_debt = sum([c[5] for c in collaterals_list])
        available_collateral = sum([c[7] for c in collaterals_list])

        collaterals_list = [
            [
                link(c[0], "/collateral/%s" % c[0], "Vaults using %s" % c[0]),
                "{0:,d}".format(c[1]),
                "{0:,d}".format(c[2]),
                "{0:,.2f}".format(c[3]),
                "{0:,.2f}".format(c[4]),
                "{0:,.2f}".format(c[5]),
                "{0:,.2f}".format(c[6]),
                "{0:,.2f}%".format(100 * c[8]) if c[8] else "-",
            ]
            for c in collaterals_list
        ]

        if not sin:
            sin = 0

        total_debt = total_debt + sin

        collaterals_data = []
        for i in collaterals_list:
            collaterals_data.append(
                dict(
                    COLLATERAL=i[0],
                    ACTIVE_VAULTS=i[1],
                    TOTAL_VAULTS=i[2],
                    LOCKED_VALUE=i[3],
                    TOTAL_DEBT=i[4],
                    AVAILABLE_DEBT=i[5],
                    AVAILABLE_COLLATERAL=i[6],
                    COLLATERALIZATION=i[7],
                )
            )

        total_collateralization = (
            "{0:,.2f}%".format(100 * locked_value / total_debt)
            if locked_value and total_debt and total_debt > 1e-10
            else "-"
        )
        debt_ceiling = "{0:,.0f}".format(Line)
        debt_utilization = "{0:,.2f}%".format(100 * total_debt / Line) if Line else ""
        total_debt = "{0:,.2f}".format(total_debt)
        locked_value = "{0:,.2f}".format(locked_value)
        available_debt = "{0:,.2f}".format(available_debt) if available_debt else "0"
        available_collateral = (
            "{0:,.2f}".format(available_collateral) if available_collateral else "0"
        )
        vaults_num = "{0:,d}".format(vaults_num)
        active_num = "{0:,d}".format(active_num) if active_num else "0"
        owners_num = "{0:,d}".format(len(owners))
        active_owners_num = "{0:,d}".format(len(active_owners))

        # coll_buckets = list(coll_buckets.items())
        # coll_buckets.sort(key=lambda _c: _c[0])

        # coll_buckets_stable = list(coll_buckets_stable.items())
        # coll_buckets_stable.sort(key=lambda _c: _c[0])

        # plot = main_collateralization_graph(coll_buckets_stable, coll_buckets)

        # sunburst_data = sf.execute("""
        #     select concat(type, '-', token, '-', ilk) ID, *
        #     from (select case
        #     when SPLIT_PART(v.ilk, '-', 0) = 'PSM' then 'PSM'
        #     when SPLIT_PART(v.ilk, '-', 0) = 'DIRECT' then 'D3M'
        #     when v.ilk like 'GUNIV3%' then 'GUNIV3'
        #     when type = 'coin' then 'TOKEN'
        #     when type = 'lp' then 'LP TOKEN'
        #     else upper(i.type)
        #     end type, v.ilk,
        #     case
        #     when SPLIT_PART(v.ilk, '-', 0) = 'PSM' then SPLIT_PART(v.ilk, '-', 2)
        #     else SPLIT_PART(v.ilk, '-', 0)
        #     end token,
        #     sum( v.collateral * v.osm_price ) value_locked, sum( v.debt ) debt
        #     from mcd.public.current_vaults v
        #     join mcd.internal.ilks i
        #     on v.ilk = i.ilk
        #     where v.ilk not like 'RWA00%' and collateral != 0
        #     group by i.type, v.ilk
        #     order by value_locked desc) as t;
        # """).fetchall()

        # sunburst_tokens = list()
        # sunburst_stablecoins = list()
        # sunburst_psm = list()
        # sunburst_others = list()

        # for id, type, ilk, token, value_locked, debt in sunburst_data:
            
        #     if type == 'STABLECOIN':
        #         sunburst_stablecoins.append([id, type, ilk, token, value_locked, debt])
        #     elif type == 'TOKEN':
        #         sunburst_tokens.append([id, type, ilk, token, value_locked, debt])
        #     elif type == 'PSM':
        #         sunburst_psm.append([id, type, ilk, token, value_locked, debt])
        #     else:
        #         sunburst_others.append([id, type, ilk, token, value_locked, debt])

        # s_tokens = main_sunburst(sunburst_tokens, 'tempo')
        # s_stablecoins = main_sunburst(sunburst_stablecoins, 'portland')
        # s_psm = main_sunburst(sunburst_psm, 'agsunset')
        # s_others = main_sunburst(sunburst_others, 'picnic')

        pie = main_pie(pie_data)
        bar = main_bar(bar_data)

        sin = "{0:,.2f}".format(sin)

        return dict(
            status="success",
            data=dict(
                total_debt=total_debt,
                collaterals=collaterals_data,
                collaterals_num=len(ilks),
                vaults_num=vaults_num,
                active_num=active_num,
                debt_ceiling=debt_ceiling,
                debt_utilization=debt_utilization,
                available_debt=available_debt,
                available_collateral=available_collateral,
                owners=owners_num,
                active_owners=active_owners_num,
                collateralization=total_collateralization,
                locked_value=locked_value,
                refresh=datetime.utcnow(),
                sin=sin,
                pie=pie,
                bar=bar
            ),
        )

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
