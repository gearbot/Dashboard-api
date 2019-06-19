from starlette.responses import JSONResponse

unauthorized_response = JSONResponse({"status": "Unauthorized"}, status_code=401)
bad_request_response = JSONResponse({"status": "BAD REQUEST"}, status_code=400)
failed_response = JSONResponse({"status": "Failed"}, status_code=500)