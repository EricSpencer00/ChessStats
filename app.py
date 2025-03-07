from flask import Flask, render_template_string, request, redirect, url_for
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Base endpoints for the Chess.com Public API.
BASE_PROFILE_URL = "https://api.chess.com/pub/player/{}"
BASE_STATS_URL = "https://api.chess.com/pub/player/{}/stats"

# The home page HTML template.
# This page includes a form to input a Chess.com username.
INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Chess.com Stats Viewer</title>
  <!-- Using Bootstrap 4 from a CDN for modern 2016 styling -->
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
  <style>
    body {
      background-color: #f0f0f0; /* Gray background */
      font-family: 'Roboto', sans-serif;
    }
    .container {
      margin-top: 50px;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1 class="text-center mb-4">Chess.com Stats Viewer</h1>
    <form method="get" action="{{ url_for('user') }}">
      <div class="form-group">
        <label for="username">Enter Chess.com Username:</label>
        <input type="text" class="form-control" id="username" name="username" placeholder="e.g., erik" required>
      </div>
      <button type="submit" class="btn btn-primary btn-block">View Stats</button>
    </form>
  </div>
</body>
</html>
'''

# The user page HTML template.
# This page shows profile info and an accordion (dropdown) for each stats category.
USER_HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Stats for {{ profile.username }}</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
  <style>
    body {
      background-color: #f0f0f0;
      font-family: 'Roboto', sans-serif;
    }
    .container {
      margin-top: 50px;
    }
    .card {
      margin-bottom: 10px;
    }
    .card-header {
      cursor: pointer;
    }
  </style>
  <!-- Include jQuery and Bootstrap JS for the accordion functionality -->
  <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"></script>
</head>
<body>
  <div class="container">
    <h2 class="text-center">Stats for {{ profile.username }}</h2>
    <div class="mb-4 text-center">
      {% if profile.avatar %}
        <img src="{{ profile.avatar }}" alt="Avatar" class="img-thumbnail" style="max-width: 200px;">
      {% endif %}
      <p><strong>Name:</strong> {{ profile.name if profile.name else "N/A" }}</p>
      <p><strong>Country:</strong> {{ profile.country }}</p>
      <p><strong>Joined:</strong> {{ profile.joined | datetimeformat }}</p>
      <p><strong>Last Online:</strong> {{ profile.last_online | datetimeformat }}</p>
      <p><strong>Status:</strong> {{ profile.status }}</p>
      <p><strong>Followers:</strong> {{ profile.followers }}</p>
    </div>

    <h3>Player Stats</h3>
    <div id="accordion">
      {# Loop over each stat category (e.g., chess_daily, chess_blitz, tactics, etc.) #}
      {% for category, data in stats.items() %}
      <div class="card">
        <div class="card-header" id="heading{{ loop.index }}" data-toggle="collapse" data-target="#collapse{{ loop.index }}" aria-expanded="true" aria-controls="collapse{{ loop.index }}">
          <h5 class="mb-0">{{ category.replace('_', ' ').title() }}</h5>
        </div>
        <div id="collapse{{ loop.index }}" class="collapse" aria-labelledby="heading{{ loop.index }}" data-parent="#accordion">
          <div class="card-body">
            <pre>{{ data | tojson(indent=2) }}</pre>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
    <a href="{{ url_for('index') }}" class="btn btn-secondary btn-block mt-3">Search Another User</a>
  </div>
</body>
</html>
'''

# A Jinja2 filter to format Unix timestamps into readable datetime strings.
@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return value

# Route for the home page.
@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

# Route for displaying a user's profile and stats.
@app.route('/user')
def user():
    username = request.args.get('username', '').strip().lower()
    if not username:
        return redirect(url_for('index'))

    # Fetch the profile data from Chess.com
    profile_url = BASE_PROFILE_URL.format(username)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    profile_response = requests.get(profile_url, headers=headers)

    # print("Profile URL:", profile_url)
    # print("Status code:", profile_response.status_code)
    # print("Response text:", profile_response.text)
    if profile_response.status_code != 200:
        return f"<h3>Error:</h3><p>Could not retrieve profile for '{username}'. Please check the username and try again.</p>", 404
    profile_data = profile_response.json()

    # Fetch the stats data from Chess.com.
    stats_url = BASE_STATS_URL.format(username)
    stats_response = requests.get(stats_url)
    # If the stats endpoint returns an error, we simply show an empty dict.
    if stats_response.status_code != 200:
        stats_data = {}
        print("Error:", stats_response.text)
    else:
        stats_data = stats_response.json()

    print("Stats URL:", stats_url)
    print(stats_data)
    # Render the user page template with profile and stats
    return render_template_string(USER_HTML, profile=profile_data, stats=stats_data)

if __name__ == '__main__':
    app.run(debug=True)
