import pytest

# Link what responses we can to one point to keep changes easier
from Utils.Responses import successful_action_response, no_reply_response

from tests import tools

noauth_client = tools.generate_noauth_client()


# TODO: Make a test for when the bot is offline

class TestOther():
    def test_metrics(self):
        resp = noauth_client.get("/api/metrics")

        tools.assure_ok_response(resp)

        # Basic sanity check
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

    def test_spinning(self):
        auth_client = tools.generate_authed_client()
        resp = auth_client.get("/api/spinning")

        tools.assure_ok_response(resp)

        tools.assure_bool(resp)

    # See pytest.ini on how to run this test
    @pytest.mark.bot_offline
    def test_bot_offline(self):
        # Test to assure the API handles a bot outage properly
        resp = tools.make_bot_request("/api/whoami")

        tools.assure_identical_response(resp, no_reply_response)
       
        

class TestMain():
    def test_logout_noauth(self): tools.assure_noauth(noauth_client.get("/api/logout"))
    def test_logout(self):
        auth_client = tools.generate_authed_client()
        resp = auth_client.get("/api/logout")
        
        tools.assure_ok_response(resp)

        assert resp.content == successful_action_response.body

        # Assure that the session was cleared properly
        assert resp.cookies.items() == []


    def test_whoami_noauth(self): tools.assure_noauth(noauth_client.get("/api/whoami"))
    def test_whoami(self):
        resp = tools.make_bot_request("/api/whoami")

        tools.assure_ok_response(resp)

        # Make sure all expected fields exist, and that they are the right type
        resp: dict = resp.json()
        tools.assure_fields_and_types(resp, ["username", "discrim", "avatar_url", "bot_admin_status"])
        # Make sure the discriminator can always be converted into a number
        assert int(resp["discrim"])

    def test_generalinfo(self):
        resp = tools.make_bot_request("/api/general_info")

        tools.assure_ok_response(resp)

        tools.assure_fields_and_types(resp.json(), ["languages", "logging"])

