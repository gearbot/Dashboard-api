from tortoise.exceptions import FieldError
from tortoise.query_utils import Q

from Utils.DataModels import Infraction


def field_concat(prefix):
    def _actual(field_name):
        return f"{field_name}__{prefix}"

    return _actual


CONVERTERS = {
    "GREATER_THAN": field_concat("gt"),
    "GREATER_OR_EQUAL_THAN": field_concat("gte"),
    "SMALLER_THAN": field_concat("lt"),
    "SMALLER_OR_EQUAL_THAN": field_concat("lte"),
    "EQUALS": lambda f: f
}


def assemble_Q(question):
    # re-assemble Q object
    direct_filters = {
        CONVERTERS[s['type']](s['field']): s['value'] for s in question["set"]
    }
    filters = [assemble_Q(q) for q in question['subFilters']]
    return Q(Q(**direct_filters), Q(*filters), join_type=question["mode"])


async def inf_search(websocket, question=None, guild_id=None, page=1, order_by=None, per_page=10):
    if order_by is None:
        order_by = ["-id"]
    if not str(guild_id).isnumeric():
        return dict(error=True, message="Not a guild id")
    if not isinstance(per_page, int):
        return dict(error=True, message="please send me an actual page limit")
    if per_page < 10 or per_page > 100:
        return dict(error=True, message="per_page must be between 10 and 100")
    if websocket.auth_info is None or "guild_infractions" not in websocket.active_subscriptions or \
            websocket.active_subscriptions["guild_infractions"] != guild_id:
        return dict(error=True, message="Unauthorized")

    guild_id = int(guild_id)
    guild_Q = Q(guild_id=guild_id)

    master_filter = Q(guild_Q, assemble_Q(question), join_type=Q.AND)

    count = await Infraction.filter(master_filter).count()
    if (page - 1) * per_page > count:
        return dict(error=True, message="Invalid page")
    try:
        infractions = await Infraction \
            .filter(master_filter) \
            .order_by(*order_by) \
            .offset((page - 1) * per_page) \
            .limit(per_page)
    except FieldError as error:
        return dict(error=True, message=str(error))

    reply = {
        "infraction_count": count,
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
