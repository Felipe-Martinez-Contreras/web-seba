from django.contrib.auth import SESSION_KEY


class CorteDeSesionMiddleware:
    """Elimina la sesión cuyo usuario ya no puede acceder (AUT-11).

    El backend deja de reconocer en la petición siguiente a un usuario desactivado o de
    una empresa desactivada. Aquí además se borra esa sesión, con todo lo que guardaba
    (incluida la verificación 2FA), para que no reviva si la cuenta se reactiva.
    Debe ir después de AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if SESSION_KEY in request.session and not request.user.is_authenticated:
            request.session.flush()
        return self.get_response(request)
