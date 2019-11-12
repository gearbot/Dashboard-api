from tortoise.exceptions import FieldError
from tortoise.query_utils import Q

from Utils.DataModels import Infraction


async def inf_search(websocket, question=None, guild_id=None, page=1, order_by=None):
    if order_by is None:
        order_by = ["-id"]
    if not str(guild_id).isnumeric():
        return dict(error=True, message="Not a guild id")
    if websocket.auth_info is None or "guild_infractions" not in websocket.active_subscriptions or \
            websocket.active_subscriptions["guild_infractions"] != guild_id:
        return dict(error=True, message="Unauthorized")
    guild_id = int(guild_id)

    filter = Q(guild_id=guild_id)

    count = await Infraction.filter(filter).count()
    try:
        infractions = await Infraction\
            .filter(filter)\
            .order_by(*order_by)\
            .offset((page - 1) * 50)\
            .limit(50)
    except FieldError as error:
        return dict(error=True, message=str(error))

    reply = {
        "count": count,
        "infraction_list": [
            {
                "id": i.id,
                "guild_id": str(i.guild_id),
                "user_id": str(i.user_id),
                "mod_id": str(i.mod_id),
                "type": i.type,
                "reason": i.reason,
                "start": i.start.isoformat(),
                "end": i.end.isoformat() if i.end else None,
                "active": i.active
            }
            for i in infractions]
    }

    return reply
