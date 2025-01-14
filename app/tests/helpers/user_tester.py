import re
from typing import Tuple

from django.conf import settings
from django.core import mail
from django.test import Client

from app.models import User, SignupLocation, Game, Player, Moderator, ParticipantRole


class UserTester:
    """
    UserTester is responsible for the creation of users and players in tests. UserTester
    does its best to emulate how real users and players are created by creating a
    django.test.Client and subsequently POSTing and GETing to the appropriate urls.
    """

    def __init__(self):
        self.client = Client()
        if not User.objects.filter(email="root@email.com").exists():
            user = User.objects.create_superuser("root@email.com", "toor")
        if not Game.objects.filter(name="Test Game").exists():
            game = Game.objects.create_game("Test Game")
        if not SignupLocation.objects.filter(name="In a Test").exists():
            game = Game.objects.get(name="Test Game")
            SignupLocation.objects.create_signup_location("In a Test", game=game)
        if not Player.objects.filter(user=user, game=game).exists():
            Moderator.objects.create_moderator(user, game)

    def create_user_and_player(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str = "password",
        game_name: str = "Test Game",
        signup_location_name: str = "In a Test",
        in_oz_pool: str = "off",
    ) -> Tuple[User, Player]:
        user = self.create_user(
            email, first_name, last_name, password, signup_location_name
        )
        player = self.create_player(email, game_name, password, in_oz_pool)
        return user, player

    def create_user(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password: str = "password",
        signup_location_name: str = "In a Test",
    ) -> User:
        self.client.login(username="root@email.com", password="toor")
        signup_location = SignupLocation.objects.get(name=signup_location_name)

        self.client.post(
            "/dashboard/volunteer/signup-players",
            {"email": email, "location": signup_location.id},
        )
        # Somewhere in the last email sent should be a signup url that looks something like this.
        regex = f"({settings.SITE_URL}/signup/.+)"
        signup_url = re.search(regex, mail.outbox[-1].body).group(1)

        # This will redirect so we "follow" the url by doing "response.url" in the next request.
        response = self.client.get(signup_url)
        self.client.post(
            response.url,
            {
                "first_name": first_name,
                "last_name": last_name,
                "password1": password,
                "password2": password,
            },
        )
        return User.objects.get(email=email)

    def create_player(
        self,
        email: str,
        game_name: str = "Test Game",
        password: str = "password",
        in_oz_pool: str = "off",
    ) -> Player:
        self.client.login(username=email, password=password)
        game = Game.objects.get(name=game_name)

        regex = f"({settings.SITE_URL}/signup/.+)"
        signup_url = re.search(regex, mail.outbox[-1].body).group(1)

        response = self.client.get(signup_url)
        self.client.post(response.url, {"is_oz": in_oz_pool, "accept_waiver": "on"})
        return User.objects.get(email=email).player_set.get(game=game, active=True)
