from django.contrib.auth.views import LoginView, LogoutView


class BootstrapLoginView(LoginView):
    template_name = "core/auth/login.html"


class BootstrapLogoutView(LogoutView):
    pass
