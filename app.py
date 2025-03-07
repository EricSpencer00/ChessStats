from flask import Flask, render_template_string, request, redirect, url_for
import requests, json, re
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Base endpoints for the Chess.com Public API.
BASE_PROFILE_URL = "https://api.chess.com/pub/player/{}"
BASE_STATS_URL = "https://api.chess.com/pub/player/{}/stats"
BASE_ARCHIVES_URL = "https://api.chess.com/pub/player/{}/games/archives"

# ----------------------------
# HTML Templates
# ----------------------------

INDEX_HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Chess.com Stats Viewer</title>
  <!-- Bootstrap 4 for modern styling -->
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
  <style>
    body { background-color: #f0f0f0; font-family: 'Roboto', sans-serif; }
    .container { margin-top: 50px; }
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
      <button type="submit" class="btn btn-primary btn-block">View Stats & Graphs</button>
    </form>
  </div>
</body>
</html>
'''

USER_HTML = '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Stats for {{ profile.username }}</title>
  <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css">
  <style>
    body { background-color: #f0f0f0; font-family: 'Roboto', sans-serif; }
    .container { margin-top: 50px; }
    .card { margin-bottom: 10px; }
    .card-header { cursor: pointer; }
  </style>
  <!-- jQuery, Popper, Bootstrap JS, and Chart.js -->
  <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js"></script>
  <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
  <div class="container">
    <h2 class="text-center">Stats for {{ profile.username }}</h2>
    <div class="mb-4 text-center">
      {% if profile.avatar %}
        <img src="{{ profile.avatar }}" alt="Avatar" class="img-thumbnail" style="max-width: 200px;">
      {% endif %}
      <p><strong>Name:</strong> {{ profile.name if profile.name else "N/A" }}</p>
      <p><strong>Country:</strong> <a href="{{ profile.country }}" target="_blank">{{ profile.country.split('/')[-1] if profile.country else 'N/A' }}</a></p>
      <p><strong>Joined:</strong> {{ profile.joined | datetimeformat }}</p>
      <p><strong>Last Online:</strong> {{ profile.last_online | datetimeformat }}</p>
      <p><strong>Status:</strong> {{ profile.status }}</p>
      <p><strong>Followers:</strong> {{ profile.followers }}</p>
    </div>

    <h3>Player Stats</h3>
    <div id="accordion">
      {% for category, data in stats.items() %}
      <div class="card">
        <div class="card-header" id="heading{{ loop.index }}" data-toggle="collapse" data-target="#collapse{{ loop.index }}" aria-expanded="true" aria-controls="collapse{{ loop.index }}">
          <h5 class="mb-0">{{ category.replace('_', ' ').title() }}</h5>
        </div>
        <div id="collapse{{ loop.index }}" class="collapse {% if loop.first %}show{% endif %}" aria-labelledby="heading{{ loop.index }}" data-parent="#accordion">
          <div class="card-body">
            {% if data is mapping %}
              {% if data.get('last') or data.get('best') or data.get('record') %}
                {% set last = data.get('last', {}) %}
                {% set best = data.get('best', {}) %}
                {% set record = data.get('record', {}) %}
                <h6>Last</h6>
                <table class="table table-sm">
                  <tr>
                    <th>Rating</th>
                    <th>Date</th>
                    <th>RD</th>
                  </tr>
                  <tr>
                    <td>{{ last.rating or 'N/A' }}</td>
                    <td>{{ last.date | datetimeformat if last.date else 'N/A' }}</td>
                    <td>{{ last.rd if last.rd is defined and last.rd is not none else 'N/A' }}</td>
                  </tr>
                </table>
                <h6>Best</h6>
                <table class="table table-sm">
                  <tr>
                    <th>Rating</th>
                    <th>Date</th>
                    <th>Game</th>
                  </tr>
                  <tr>
                    <td>{{ best.rating or 'N/A' }}</td>
                    <td>{{ best.date | datetimeformat if best.date else 'N/A' }}</td>
                    <td>{% if best.game %}<a href="{{ best.game }}" target="_blank">View Game</a>{% else %}N/A{% endif %}</td>
                  </tr>
                </table>
                <h6>Record</h6>
                <table class="table table-sm">
                  <tr>
                    <th>Win</th>
                    <th>Loss</th>
                    <th>Draw</th>
                  </tr>
                  <tr>
                    <td>{{ record.win or 0 }}</td>
                    <td>{{ record.loss or 0 }}</td>
                    <td>{{ record.draw or 0 }}</td>
                  </tr>
                </table>
              {% else %}
                <pre>{{ data | tojson(indent=2) }}</pre>
              {% endif %}
            {% else %}
              <pre>{{ data }}</pre>
            {% endif %}
          </div>
        </div>
      </div>
      {% endfor %}
    </div>

    <!-- Graph Options Form -->
    <h3 class="mt-4">Rating History Graph</h3>
    <form method="get" action="{{ url_for('user') }}">
      <!-- Preserve the username -->
      <input type="hidden" name="username" value="{{ profile.username }}">
      <div class="form-row">
        <div class="col-md-4">
          <label for="time_period">Time Period:</label>
          <select class="form-control" name="time_period" id="time_period">
            <option value="past_3_months" {% if time_period == 'past_3_months' %}selected{% endif %}>Past 3 Months</option>
            <option value="past_year" {% if time_period == 'past_year' %}selected{% endif %}>Past Year</option>
            <option value="all_time" {% if time_period == 'all_time' %}selected{% endif %}>All Time</option>
          </select>
        </div>
        <div class="col-md-8">
          <label>Game Types:</label><br>
          {% for cat in graph_data.keys()|list %}
            <div class="form-check form-check-inline">
              <input class="form-check-input" type="checkbox" name="category" value="{{ cat }}" id="cat_{{ cat }}"
                {% if not selected_categories or cat in selected_categories %}checked{% endif %}>
              <label class="form-check-label" for="cat_{{ cat }}">{{ cat.title() }}</label>
            </div>
          {% endfor %}
        </div>
      </div>
      <button type="submit" class="btn btn-info mt-2">Update Graph</button>
    </form>

    <!-- Graph Canvas -->
    <div class="mt-4">
      <canvas id="ratingChart" width="800" height="400"></canvas>
    </div>

    <a href="{{ url_for('index') }}" class="btn btn-secondary btn-block mt-3">Search Another User</a>
  </div>

  <script>
    // Parse graph data passed from Flask
    const graphData = {{ graph_data_json | safe }};
    // Determine which categories are selected (based on form checkboxes)
    let selectedCategories = [];
    document.querySelectorAll('input[name="category"]:checked').forEach(el => {
      selectedCategories.push(el.value);
    });
    
    // Build Chart.js datasets for selected categories.
    const datasets = [];
    const colors = {
      "daily": "rgba(255, 99, 132, 0.6)",
      "rapid": "rgba(54, 162, 235, 0.6)",
      "blitz": "rgba(255, 206, 86, 0.6)",
      "bullet": "rgba(75, 192, 192, 0.6)"
    };

    for (const [cat, points] of Object.entries(graphData)) {
      if (selectedCategories.length && !selectedCategories.includes(cat)) continue;
      // Convert points to the format: {x: date, y: rating}
      const dataPoints = points.map(pt => ({ x: new Date(pt.x * 1000), y: pt.y }));
      datasets.push({
        label: cat.charAt(0).toUpperCase() + cat.slice(1),
        data: dataPoints,
        fill: false,
        borderColor: colors[cat] || 'rgba(0,0,0,0.6)',
        tension: 0.1
      });
    }

    const ctx = document.getElementById('ratingChart').getContext('2d');
    const ratingChart = new Chart(ctx, {
      type: 'line',
      data: {
        datasets: datasets
      },
      options: {
        plugins: {
          title: { display: true, text: 'Rating History' }
        },
        scales: {
          x: { type: 'time', time: { unit: 'month' }, title: { display: true, text: 'Date' } },
          y: { title: { display: true, text: 'Rating' } }
        }
      }
    });
  </script>
</body>
</html>
'''

# ----------------------------
# Jinja Filters
# ----------------------------

@app.template_filter('datetimeformat')
def datetimeformat(value):
    try:
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return value

# ----------------------------
# Routes
# ----------------------------

@app.route('/')
def index():
    return render_template_string(INDEX_HTML)

@app.route('/user')
def user():
    # Get username (preserve case)
    username = request.args.get('username', '').strip()
    if not username:
        return redirect(url_for('index'))

    # Graph options from query parameters
    time_period = request.args.get('time_period', 'past_year')
    selected_categories = request.args.getlist('category')

    # Prepare headers (simulate a browser)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    # Fetch profile data
    profile_url = BASE_PROFILE_URL.format(username)
    profile_response = requests.get(profile_url, headers=headers)
    if profile_response.status_code != 200:
        return f"<h3>Error:</h3><p>Could not retrieve profile for '{username}'. Please check the username and try again.</p>", 404
    profile_data = profile_response.json()

    # Fetch stats data
    stats_url = BASE_STATS_URL.format(username)
    stats_response = requests.get(stats_url, headers=headers)
    stats_data = stats_response.json() if stats_response.status_code == 200 else {}

    # ----------------------------
    # Build Graph Data from Monthly Archives
    # ----------------------------
    graph_data = {}
    default_categories = ["daily", "rapid", "blitz", "bullet"]

    now = datetime.now()
    if time_period == "past_3_months":
        cutoff_date = now - timedelta(days=90)
    elif time_period == "past_year":
        cutoff_date = now - timedelta(days=365)
    elif time_period == "all_time":
        cutoff_date = datetime.min
    else:
        cutoff_date = now - timedelta(days=365)

    archives_url = BASE_ARCHIVES_URL.format(username)
    archives_response = requests.get(archives_url, headers=headers)
    if archives_response.status_code == 200:
        archives_list = archives_response.json().get('archives', [])
        filtered_archives = []
        for arch in archives_list:
            m = re.search(r'/(\d{4})/(\d{2})$', arch)
            if m:
                year = int(m.group(1))
                month = int(m.group(2))
                archive_date = datetime(year, month, 1)
                if archive_date >= cutoff_date:
                    filtered_archives.append(arch)
        for arch_url in filtered_archives:
            arch_response = requests.get(arch_url, headers=headers)
            if arch_response.status_code != 200:
                continue
            games = arch_response.json().get('games', [])
            for game in games:
                if 'end_time' not in game:
                    continue
                game_type = game.get('time_class', None)
                if not game_type:
                    continue
                user_in_game = False
                rating = None
                if game.get('white', {}).get('username', '').lower() == username.lower():
                    user_in_game = True
                    rating = game.get('white', {}).get('rating', None)
                elif game.get('black', {}).get('username', '').lower() == username.lower():
                    user_in_game = True
                    rating = game.get('black', {}).get('rating', None)
                if user_in_game and rating is not None:
                    if game_type not in graph_data:
                        graph_data[game_type] = []
                    graph_data[game_type].append({ "x": game.get('end_time'), "y": rating })
    for cat in default_categories:
        if cat not in graph_data:
            graph_data[cat] = []

    if not selected_categories:
        selected_categories = list(graph_data.keys())

    graph_data_json = json.dumps(graph_data)

    return render_template_string(USER_HTML, profile=profile_data, stats=stats_data,
                                  graph_data=graph_data, graph_data_json=graph_data_json,
                                  time_period=time_period, selected_categories=selected_categories)

if __name__ == '__main__':
    app.run(debug=True)
