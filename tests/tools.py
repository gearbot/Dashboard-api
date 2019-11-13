from starlette.testclient import TestClient
from starlette.responses import Response

from api import app

from Utils.Configuration import config
from Utils.Responses import unauthorized_response

# Setup for tests...
session = config["testing_info"]["session"]
assert session

user_id = config["testing_info"]["user_id"]
assert user_id

guild_id = config["testing_info"]["guild_id"]
assert guild_id

guild_mute_role = config["testing_info"]["guild_mute_role"]
assert guild_mute_role

valid_bool_conversions = ["True", "true", "False", "false"]

def generate_noauth_client():
    return TestClient(app)

def generate_authed_client():
    testclient = TestClient(app)
    testclient.cookies.set("session", session)
    return testclient

def make_bot_request(url: str, method: str = "GET", body: dict = None):
    with TestClient(app) as testclient:
        testclient.cookies.set("session", session)
        
        # Allow to send POST or PATCH requests with no body for possible test cases
        if body == None:
            resp = testclient.request(method, url)
        else:
            if method == "POST":
                resp = testclient.post(url, json=body)
            elif method == "PATCH":
                resp = testclient.patch(url, json=body)
        return resp

def generate_guildapi_path():
    return f"/api/guilds/{guild_id}/"

def get_mute_role():
    return guild_mute_role

def assure_noauth(resp: Response):
    print(resp.content)
    assert resp.status_code == 401
    assert resp.content == unauthorized_response.body

def assure_ok_response(resp: Response):
    assert resp.status_code == 200

    # All responses should have *something* in them
    assert int(resp.headers["content-length"]) > 1

def assure_identical_response(resp: Response, expected: Response):
    assert resp.status_code == expected.status_code
    assert resp.content == expected.body

def assure_bool(resp: Response):
    resp = resp.content.decode("utf-8")
    assert resp in valid_bool_conversions

def assure_types(section: dict, deep: bool = False):
    if deep:
        sunken_section = {}
        for _, fields in section.items():
            sunken_section.update(fields)
        section = sunken_section

    for k, v in section.items():
            if type(v) != field_types[k]: # Easy hunting when debugging
                print(f"The type should be {field_types[k]}, but it was seen as {type(v)}!")

            assert type(v) == field_types[k]
            # Make sure the IDs are actually IDs
            if k == "id": assert int(v)
                    

def assure_fields(section: dict, required_fields: list, deep: bool = False):
    if not deep:
        assert list(section.keys()) == required_fields
    else:
      for _, fields in section.items():
        assert list(fields.keys()) == required_fields

def assure_fields_and_types(section: dict, required_fields: list, deep: bool = False):
    assure_fields(section, required_fields, deep)
    assure_types(section, deep)
            
field_types = {
    "username": str,
    "discrim": str,
    "avatar_url": str,
    "bot_admin_status": bool,
    "languages": dict,
    "logging": dict,
    "id": str,
    "name": str,
    "permissions": int,
    "icon": str,
    "server_icon": str,
    "owner": dict,
    "members": int,
    "text_channels": dict,
    "can_log": bool,
    "additional_text_channels": dict,
    "voice_channels": int,
    "creation_date": str,
    "age_days": int,
    "vip_features": list,
    "role_list": dict,
    "color": str,
    "is_admin": bool,
    "is_mod": bool,
    "can_be_self_role": bool,
    "emojis": list,
    "member_statuses": dict,
    "member_statuses_count": int,
    "user_perms": int,
    "user_level": int,
    "status": str,
    "errors": dict,
    "modified_values": dict
}