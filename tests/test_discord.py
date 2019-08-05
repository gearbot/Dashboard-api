from tests import tools
from tests.tools import CLIENT_URL

from Utils.Responses import bad_oauth_response

noauth_client = tools.generate_noauth_client()

def test_oauth_redir():
    resp = noauth_client.request("GET", "/api/discord/login", allow_redirects=False)

    # Make sure the redirect is formatted correctly
    assert resp.status_code == 307

    # Make sure that the state key is always present and set correctly
    assert "state_key" in resp.cookies
    location_parts = str(resp.headers["location"]).split("&")
    assert resp.cookies["state_key"] in location_parts[1]

def test_oauth_callback():
    # These tests ensures all the proper protections are in place, not the actual OAuth flow

    # No state key
    resp = noauth_client.request("GET", "/api/discord/callback", allow_redirects=False)    
    tools.assure_identical_response(resp, bad_oauth_response)

    # No OAuth code
    state_key = "spooky"
    resp = noauth_client.request(
        "GET", 
        f"/api/discord/callback?state={state_key}", 
        allow_redirects = False,
        cookies = {"state_key": state_key}
    )
    tools.assure_identical_response(resp, bad_oauth_response)

    # Make sure we handle user OAuth denials properly
    resp = noauth_client.request("GET", "/api/discord/callback?error=denied", allow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == CLIENT_URL
