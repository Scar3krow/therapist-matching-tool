from flask import Flask, render_template, request, session
import pandas as pd
import requests
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session to work

# Load the Google Sheets data from the CSV export link
def load_excel_data():
    # Google Sheets CSV export link
    file_url = "https://docs.google.com/spreadsheets/d/1leIVHKD7O2rIXeTTT7wDMht_USxL9X2U/export?format=csv"

    # Request the CSV file from Google Sheets
    response = requests.get(file_url)

    if response.status_code == 200:
        # Read the CSV file into a pandas DataFrame directly from text using StringIO
        df = pd.read_csv(StringIO(response.text))
    else:
        raise Exception(f"Failed to download the file from Google Sheets: {response.status_code}")

    # Define section headers that indicate the start of each section
    section_headers = {
        'AREA OF PRACTICE': [],
        'AGE/ CLIENT TYPE': [],
        'INTERVENTIONS': [],
        'AREAS OF WORK': []
    }

    # Loop through the dataset and categorize rows under each section
    current_category = None
    for i, row in df.iterrows():
        first_cell = str(row['CLINICIAN']).strip()

        # Check if the row contains a section header
        if first_cell in section_headers:
            current_category = first_cell
            continue
        
        # Assign rows to the current category
        if current_category and not pd.isna(first_cell):
            section_headers[current_category].append(first_cell)

    # Extract sections from the dictionary
    area_of_practice = section_headers['AREA OF PRACTICE']
    age_client_type = section_headers['AGE/ CLIENT TYPE']
    interventions = section_headers['INTERVENTIONS']
    areas_of_work = section_headers['AREAS OF WORK']
    
    # Extract clinician names (columns)
    clinicians = df.columns[1:].tolist()  # Skip the first "CLINICIAN" column
    
    # Add default options at the beginning
    area_of_practice.insert(0, "Select Area of Practice")
    age_client_type.insert(0, "Select Age/ Client Type")
    interventions.insert(0, "Select Intervention")
    areas_of_work.insert(0, "Select Area of Work")

    return df, area_of_practice, age_client_type, interventions, areas_of_work, clinicians

# Calculate clinician ratings based on selected categories
def calculate_ratings(df, selected_area, selected_age, selected_intervention, selected_work_areas, clinicians):
    clinician_scores = {}

    # Convert all columns that contain numerical ratings to numeric type (int or float)
    df[clinicians] = df[clinicians].apply(pd.to_numeric, errors='coerce')  # Convert columns to numeric

    # Safely find the indices for the selected rows in the dataframe
    area_index = df[df['CLINICIAN'] == selected_area].index[0] if not df[df['CLINICIAN'] == selected_area].empty and selected_area != "Select Area of Practice" else None
    age_index = df[df['CLINICIAN'] == selected_age].index[0] if not df[df['CLINICIAN'] == selected_age].empty and selected_age != "Select Age/ Client Type" else None
    intervention_index = df[df['CLINICIAN'] == selected_intervention].index[0] if not df[df['CLINICIAN'] == selected_intervention].empty and selected_intervention != "Select Intervention" else None
    
    # Handle up to 3 work areas
    work_area_indices = []
    for work_area in selected_work_areas:
        if work_area != "Select Area of Work" and not df[df['CLINICIAN'] == work_area].empty:
            work_area_indices.append(df[df['CLINICIAN'] == work_area].index[0])

    for clinician in clinicians:
        score_sum = 0
        category_count = 0

        # Check Area of Practice: Exclude clinician if Area of Practice score is 0
        if area_index is not None:
            area_score = df.iloc[area_index][clinician]
            if area_score == 0:
                continue  # Exclude clinician if Area of Practice score is 0
            score_sum += area_score
            category_count += 1

        # Check and add score for selected age/client type: Exclude clinician if score is 0
        if age_index is not None:
            age_score = df.iloc[age_index][clinician]
            if age_score == 0:
                continue  # Exclude clinicians with 0 score
            score_sum += age_score
            category_count += 1

        # Check and add score for selected intervention: Exclude clinician if score is 0
        if intervention_index is not None:
            intervention_score = df.iloc[intervention_index][clinician]
            if intervention_score == 0:
                continue  # Exclude clinicians with 0 score
            score_sum += intervention_score
            category_count += 1

        # Check and add scores for the selected areas of work but include the 0 score in average
        for work_area_index in work_area_indices:
            work_area_score = df.iloc[work_area_index][clinician]
            # Include the score even if it's 0
            score_sum += work_area_score
            category_count += 1

        # Calculate the average score (sum divided by the number of selected categories)
        if category_count > 0:
            average_score = score_sum / category_count
            clinician_scores[clinician] = round(average_score, 2)

    # Sort clinicians by their scores in descending order
    ranked_clinicians = sorted(clinician_scores.items(), key=lambda x: x[1], reverse=True)

    # Limit the results to a maximum of 8 clinicians
    ranked_clinicians = ranked_clinicians[:8]

    # Return the ranked clinicians list, which might be empty
    return ranked_clinicians


@app.route('/')
def index():
    # Load the dynamic data from Excel
    df, area_of_practice, age_client_type, interventions, areas_of_work, clinicians = load_excel_data()
    
    return render_template('index.html', 
                           areas=area_of_practice, 
                           ages=age_client_type, 
                           interventions=interventions,
                           work_areas=areas_of_work)

@app.route('/match', methods=['GET', 'POST'])
def match():
    if request.method == 'POST':
        # POST: User submitted the form
        selected_area = request.form['area']
        selected_age = request.form['age']
        selected_intervention = request.form['intervention']
        selected_work_areas = [
            request.form['work_area_1'],
            request.form['work_area_2'],
            request.form['work_area_3']
        ]
        # Store selections in the session
        session['selected_area'] = selected_area
        session['selected_age'] = selected_age
        session['selected_intervention'] = selected_intervention
        session['selected_work_areas'] = selected_work_areas
    else:
        # GET: Load previously stored selections from the session
        selected_area = session.get('selected_area', 'Select Area of Practice')
        selected_age = session.get('selected_age', 'Select Age/ Client Type')
        selected_intervention = session.get('selected_intervention', 'Select Intervention')
        selected_work_areas = session.get('selected_work_areas', ['Select Area of Work', 'Select Area of Work', 'Select Area of Work'])

    # Load the data and calculate the clinician ratings
    df, area_of_practice, age_client_type, interventions, areas_of_work, clinicians = load_excel_data()
    ranked_clinicians = calculate_ratings(df, selected_area, selected_age, selected_intervention, selected_work_areas, clinicians)

    if not ranked_clinicians:
        message = "No Qualified Therapists Available"
        return render_template('match.html', 
                               area=selected_area, 
                               age=selected_age, 
                               intervention=selected_intervention, 
                               work_areas=selected_work_areas,
                               message=message)

    return render_template('match.html', 
                           area=selected_area, 
                           age=selected_age, 
                           intervention=selected_intervention, 
                           work_areas=selected_work_areas,
                           ranked_clinicians=ranked_clinicians)

@app.route('/clinician/<clinician_name>')
def clinician_details(clinician_name):
    # Get the selected categories from the query parameters
    selected_area = request.args.get('area')
    selected_age = request.args.get('age')
    selected_intervention = request.args.get('intervention')
    selected_work_areas = [
        request.args.get('work_area_1'),
        request.args.get('work_area_2'),
        request.args.get('work_area_3')
    ]

    # Load the Excel data
    df, area_of_practice, age_client_type, interventions, areas_of_work, clinicians = load_excel_data()

    # Initialize a dictionary to store clinician ratings along with category names
    clinician_ratings = {}

    # Safely find the indices for the selected categories and include the actual category name
    if selected_area and selected_area != "Select Area of Practice":
        area_index = df[df['CLINICIAN'] == selected_area].index
        if not area_index.empty:
            clinician_ratings[selected_area] = df.iloc[area_index[0]][clinician_name]

    if selected_age and selected_age != "Select Age/ Client Type":
        age_index = df[df['CLINICIAN'] == selected_age].index
        if not age_index.empty:
            clinician_ratings[selected_age] = df.iloc[age_index[0]][clinician_name]

    if selected_intervention and selected_intervention != "Select Intervention":
        intervention_index = df[df['CLINICIAN'] == selected_intervention].index
        if not intervention_index.empty:
            clinician_ratings[selected_intervention] = df.iloc[intervention_index[0]][clinician_name]

    for i, work_area in enumerate(selected_work_areas):
        if work_area and work_area != "Select Area of Work":
            work_area_index = df[df['CLINICIAN'] == work_area].index
            if not work_area_index.empty:
                clinician_ratings[work_area] = df.iloc[work_area_index[0]][clinician_name]

    # Render the clinician details page with actual category names
    return render_template('clinician_details.html', clinician_name=clinician_name, clinician_ratings=clinician_ratings)

if __name__ == '__main__':
    app.run(debug=True)
