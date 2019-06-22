from starlette.responses import JSONResponse

unauthorized_response = JSONResponse({"status": "Unauthorized"}, status_code=401)
bad_request_response = JSONResponse({"status": "BAD REQUEST"}, status_code=400)
failed_response = JSONResponse({"status": "Failed"}, status_code=500)
no_reply_response = JSONResponse({"status": "Bot unreachable"}, status_code=500)
unknown_config_response = JSONResponse({"status": "Unknown config section"}, status_code=400)