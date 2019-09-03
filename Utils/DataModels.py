from tortoise.models import Model
from tortoise import fields


class UserInfo(Model):
    id = fields.IntField(pk=True, generated=False)  # VERY IMPORTANT TO TURN OFF GENERATED HERE
    api_token = fields.CharField(100)
    refresh_token = fields.CharField(100)
    expires_at = fields.DatetimeField()


class Dashsession(Model):
    id = fields.CharField(50, pk=True, generated=False)
    user = fields.ForeignKeyField("models.UserInfo", related_name="sessions")
    expires_at = fields.DatetimeField()
