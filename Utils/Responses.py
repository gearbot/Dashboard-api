from starlette.responses import JSONResponse, RedirectResponse

unauthorized_response = JSONResponse({"status": "Unauthorized"}, status_code=401)
bad_request_response = JSONResponse({"status": "BAD REQUEST"}, status_code=400)
failed_response = JSONResponse({"status": "Failed"}, status_code=500)
successful_action_response = JSONResponse(dict(status="Success"))
no_reply_response = JSONResponse({"status": "Bot unreachable"}, status_code=500)
unknown_config_response = JSONResponse({"status": "Unknown config section"}, status_code=400)
no_roleid_response = JSONResponse({"status": "BAD REQUEST", "errors": ["missing role_id"]}, status_code=400)
bad_oauth_response = RedirectResponse("https://i.imgur.com/vN5jG9r.mp4")