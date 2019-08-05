import pytest

# Link what responses we can to one point to keep changes easier
from Utils.Responses import unknown_config_response, bad_request_response, no_roleid_response

from tests import tools

noauth_client = tools.generate_noauth_client()

post_body = {
    "LANG": "en_US",
    "NEW_USER_THRESHOLD": 86400,
    "PERM_DENIED_MESSAGE": True,
    "PREFIX": "*",
    "TIMESTAMPS": False,
    "TIMEZONE": "Europe/Brussels"
}

patch_body = {
    "PREFIX": "#",
    "TIMESTAMPS": True,
}


class TestGuildList():
    def test_endpoint_noauth(self): tools.assure_noauth(noauth_client.get("/api/guilds/"))
    def test_endpoint(self):
        resp = tools.make_bot_request("/api/guilds/")

        tools.assure_ok_response(resp)

        for _, guild_info in resp.json().items():
            # Assure the proper fields and types exist on all guilds
            tools.assure_fields_and_types(guild_info, ["id", "name", "permissions", "icon"])

            # Make sure the permissions are in the expected range, subject to change.
            assert guild_info["permissions"] <= 15

class TestGuildStats():
    def test_endpoint_noauth(self): tools.assure_noauth(noauth_client.get(tools.generate_guildapi_path() + "info"))
    def test_endpoint(self):
        resp = tools.make_bot_request(tools.generate_guildapi_path() + "info")

        tools.assure_ok_response(resp)

        resp: dict = resp.json()
        # Assure the keys are the right type
        # Check the top-level type of the response
        tools.assure_fields_and_types(
            resp, 
            [
                "name",
                "id",
                "server_icon",
                "owner",
                "members",
                "text_channels",
                "additional_text_channels",
                "voice_channels",
                "creation_date",
                "age_days",
                "vip_features",
                "role_list",
                "emojis",
                "member_statuses",
                "user_perms",
                "user_level"
            ]
        )

        # Check the structures and their fields and types
        tools.assure_fields_and_types(resp["owner"], ["id", "name"])

        tools.assure_fields(resp["member_statuses"], ["online", "idle", "dnd", "offline"])
        for _, v in resp["member_statuses"].items():
            assert type(v) == tools.field_types["member_statuses_count"]

        tools.assure_fields_and_types(resp["text_channels"], ["name", "can_log"], deep=True)
        tools.assure_fields_and_types(resp["additional_text_channels"], ["name", "can_log"], deep=True)

        tools.assure_fields_and_types(
            resp["role_list"],
            ["id", "name", "color", "members", "is_admin", "is_mod", "can_be_self_role"],
            deep=True
        )
        for emoji in resp["emojis"]:
            tools.assure_types(emoji)
    
    def test_endpoint_invalid(self):
        # Test for a bad guild ID
        resp = tools.make_bot_request("/api/guilds/-1111/info")
        
        tools.assure_identical_response(resp, bad_request_response)
    
class TestGuildConfig():
    def test_get_endpoint_noauth(self): tools.assure_noauth(noauth_client.get(tools.generate_guildapi_path() + "config/general"))
    def test_get_endpoint(self):
        resp = tools.make_bot_request(tools.generate_guildapi_path() + "config/general")
        # Assume that if this endpoint returns JSON and a 200 OK code then it returned the right data
        assert resp.status_code == 200

        # Due to the variants of what this can return, we can only check if its a proper dict
        assert type(resp.json()) == dict

    def test_get_endpoint_invalid(self):
        # Test for a unknown section
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + r"config/%20%",
            method = "GET"
        )
        tools.assure_identical_response(resp, unknown_config_response)

        # Test for a invalid guild
        resp = tools.make_bot_request(
            f"/api/guilds/true/config/general",
            method = "GET"
        )
        # FastAPI itself denies this one as it doesnt match a proper type
        assert resp.status_code == 422


    def test_post_endpoint_noauth(self): tools.assure_noauth(noauth_client.post(tools.generate_guildapi_path() + "config/general", json=post_body))
    def test_post_endpoint(self):
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "config/general",
            method = "POST",
            body = post_body
        )
        
        tools.assure_ok_response(resp)

        tools.assure_fields_and_types(resp.json(), ["status", "modified_values"])

    def test_post_endpoint_invalid(self):
        # Test for an unknown section
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "config/''",
            method = "POST",
            body = post_body
        )
        tools.assure_identical_response(resp, unknown_config_response)

        # Test for a invalid guild
        resp = tools.make_bot_request(
            f"/api/guilds/{-1111}/config/general",
            method = "POST",
            body = post_body
        )
        tools.assure_identical_response(resp, bad_request_response)


    def test_patch_endpoint_noauth(self): tools.assure_noauth(noauth_client.patch(tools.generate_guildapi_path() + "config/general", json=patch_body))
    def test_patch_endpoint(self):
        # Test proper usage
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "config/general",
            method = "PATCH",
            body = patch_body
        )
        tools.assure_ok_response(resp)

        tools.assure_fields_and_types(resp.json(), ["status", "modified_values"])
        
        # Test duplicate update requests
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "config/general",
            method = "PATCH",
            body = patch_body
        )
        assert resp.status_code == 400
        
        tools.assure_fields_and_types(resp.json(), ["status", "errors"])

    def test_patch_endpoint_invalid(self):
        # Test for a unknown section
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "config/spooky",
            method = "PATCH",
            body = patch_body
        )
        tools.assure_identical_response(resp, unknown_config_response)

        # Test for a invalid guild
        resp = tools.make_bot_request(
            f"/api/guilds/292782/config/general",
            method = "PATCH",
            body = patch_body
        )
        tools.assure_identical_response(resp, bad_request_response)

class TestGuildMute():
    # All Role IDs are sent as integers, not strings, because validation of string handling is covered in the invalid testing
    def make_mute_post(self, mute_body: dict):
        resp = tools.make_bot_request(
            tools.generate_guildapi_path() + "mute",
            method = "POST",
            body = mute_body
        )
        return resp

    def test_mute_endpoint_noauth(self): tools.assure_noauth(noauth_client.post(tools.generate_guildapi_path() + "mute", json={"test": "bad"}))
    
    # See pytest.ini on how to run these tests
    @pytest.mark.mute
    def test_mute_endpoint(self):
        # Test mute setup
        # TODO: Makes big spam mess
        resp = self.make_mute_post({"action": "setup", "role_id": tools.get_mute_role()})
        assert resp.status_code == 200

        # Test mute cleanup
        # TODO: Disabled, makes a big spam mess
        resp = self.make_mute_post({"action": "cleanup", "role_id": tools.get_mute_role()})
        assert resp.status_code == 200

    def test_mute_endpoint_invalid(self):
        # Test for a bad guild
        resp = tools.make_bot_request(
            f"/api/guilds/{-1111}/mute",
            method = "POST",
            body = {
                "action": "setup",
                "role_id": 9999
            }
        )
        tools.assure_identical_response(resp, bad_request_response)

        # Test for request body parts, grouped for clarity
        def validate_body_parts():
            # Has action, no role_id
            resp = self.make_mute_post({"action": "setup"})
            tools.assure_identical_response(resp, no_roleid_response)

            # Has role_id, no action
            resp = self.make_mute_post({"role_id": 99999})
            tools.assure_identical_response(resp, bad_request_response)

            # Extra, unknown, fields
            resp = self.make_mute_post({"action": "setup", "role_id": 99999, "test": True})
            tools.assure_identical_response(resp, bad_request_response)

        validate_body_parts()

        # Test for a bad role_id
        resp = self.make_mute_post({"action": "cleanup", "role_id": -11111})
        tools.assure_identical_response(resp, bad_request_response)

        # Test for improper role_id type
        resp = self.make_mute_post({"action": "cleanup", "role_id": "Spooky"})
        tools.assure_identical_response(resp, bad_request_response)

        # Test for improper action type
        resp = self.make_mute_post({"action": True, "role_id": 99999})
        tools.assure_identical_response(resp, bad_request_response)

        # Test for a non-existant action
        resp = self.make_mute_post({"action": "spooky", "role_id": 99999})
        tools.assure_identical_response(resp, bad_request_response)
