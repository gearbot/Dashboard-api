from tortoise.models import Model
from tortoise import fields


class BaseModel(Model):
    class Meta:
        abstract = True

    def __str__(self):
        return self.name



class Dashsession(BaseModel):
    id = fields.CharField(50, pk=True, source_field="token", reference="token")
    user_id = fields.BigIntField()
    api_token = fields.CharField(100)
    refresh_token = fields.CharField(100)
    expires_at = fields.DatetimeField()
