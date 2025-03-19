from django.db import models

class Match(models.Model):
    home_team = models.CharField(max_length=100)
    away_team = models.CharField(max_length=100)
    home_goals = models.IntegerField(null=True)
    away_goals = models.IntegerField(null=True)
    status = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.home_team} 🆚 {self.away_team}"