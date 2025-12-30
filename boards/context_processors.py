from .models import Team, Board

def sidebar_data(request):
    """Provide teams and boards for sidebar on every page."""
    if request.user.is_authenticated:
        teams = request.user.teams.all().prefetch_related("boards")
        boards = Board.objects.filter(members=request.user)
    else:
        teams = []
        boards = []
    return {"sidebar_teams": teams, "sidebar_boards": boards}