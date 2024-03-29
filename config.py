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
from dotenv import load_dotenv
import sqlalchemy

load_dotenv()

PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))

class EnvVariableError(Exception):
    pass


def get_variable(name):
    if not os.environ.get(name):
        # load env variables from .env if .env available
        if os.path.isfile(os.path.join(PROJECT_ROOT, ".env")):
            load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
            try:
                return os.environ[name]
            except:
                raise EnvVariableError("{} not available.".format(name))
        else:
            raise EnvVariableError(".env file not available.")

    else:
        # load value from env if available
        return os.environ[name]


# Blockchain node connection
NODE = get_variable("BC_NODE")

# Snowflake connection
SNOWFLAKE_CONNECTION = dict(
    account=get_variable("SNOWFLAKE_ACCOUNT"),
    user=get_variable("SNOWFLAKE_USER"),
    password=get_variable("SNOWFLAKE_PASS"),
    warehouse="COMPUTE_WH",
    database="MCD",
)

# limit of debt for active vaults
ACTIVE_DUST_LIMIT = 20

# stablecoins
STABLECOINS = ("USDC", "USDT", "TUSD", "PAXUSD", "GUSD")

SECRET = get_variable("SECRET")

DEBUG = True

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