def success(data=None):
    return {
        "success": True,
        "data": data,
        "error": None
    }

def fail(message, code=400):
    return {
        "success": False,
        "data": None,
        "error": {
            "message": message,
            "code": code
        }
    }
