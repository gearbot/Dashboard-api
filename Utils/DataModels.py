from tortoise.models import Model
from tortoise import fields


class UserInfo(Model):
    id = fields.BigIntField(pk=True, generated=False)  # VERY IMPORTANT TO TURN OFF GENERATED HERE
    api_token = fields.CharField(100)
    refresh_token = fields.CharField(100)
    expires_at = fields.DatetimeField()


class Dashsession(Model):
    id = fields.CharField(50, pk=True, generated=False)
    user = fields.ForeignKeyField("models.UserInfo", related_name="sessions")
    expires_at = fields.DatetimeField()

class Infraction(Model):
    id = fields.IntField(pk=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    mod_id = fields.BigIntField()
    type = fields.CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = fields.DatetimeField()
    end = fields.DatetimeField(null=True)
    active = fields.BooleanField(default=True)
