from tortoise import Tortoise, run_async

from Utils.Configuration import DB_URL


async def test():
    await Tortoise.init(
        db_url=DB_URL,
        modules={'models': ['Utils.DataModels']}
    )
    # Generate the schema
    await Tortoise.generate_schemas()
    connection =  Tortoise.get_connection("default")
    await connection.execute_script("alter table apitokens modify id BIGINT")


run_async(test())