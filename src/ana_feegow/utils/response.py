def ok(message, **kwargs):
    retorno = {
        "success": True,
        "message": message,
    }

    retorno.update(kwargs)
    return retorno


def fail(message, **kwargs):
    retorno = {
        "success": False,
        "message": message,
    }

    retorno.update(kwargs)
    return retorno
