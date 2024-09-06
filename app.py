from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Load the Excel file and extract dropdown options
def load_excel_data():
    file_path = "therapist matching.xlsx"  # Update with your actual file path
    df = pd.read_excel(file_path, sheet_name="Sheet1")
    
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
def calculate_ratings(df, selected_area, selected_age, selected_intervention, selected_work_area, clinicians):
    clinician_scores = {}
    
    # Find the indices for the selected rows in the dataframe
    area_index = df[df['CLINICIAN'] == selected_area].index[0] if selected_area != "Select Area of Practice" else None
    age_index = df[df['CLINICIAN'] == selected_age].index[0] if selected_age != "Select Age/ Client Type" else None
    intervention_index = df[df['CLINICIAN'] == selected_intervention].index[0] if selected_intervention != "Select Intervention" else None
    work_area_index = df[df['CLINICIAN'] == selected_work_area].index[0] if selected_work_area != "Select Area of Work" else None
    
    for clinician in clinicians:
        score_sum = 0
        category_count = 0
        
        # Check Area of Practice: 0 excludes, 10 includes but doesn't affect score
        if area_index is not None:
            area_score = df.iloc[area_index][clinician]
            if area_score == 0:
                continue  # Exclude clinician if Area of Practice score is 0
            # No impact on score for a 10 in Area of Practice
        
        # Check and add score for selected age/client type
        if age_index is not None:
            age_score = df.iloc[age_index][clinician]
            if age_score == 0:
                continue  # Exclude clinicians with 0 score
            score_sum += age_score
            category_count += 1
        
        # Check and add score for selected intervention
        if intervention_index is not None:
            intervention_score = df.iloc[intervention_index][clinician]
            if intervention_score == 0:
                continue  # Exclude clinicians with 0 score
            score_sum += intervention_score
            category_count += 1
        
        # Check and add score for selected area of work
        if work_area_index is not None:
            work_area_score = df.iloc[work_area_index][clinician]
            if work_area_score == 0:
                continue  # Exclude clinicians with 0 score
            score_sum += work_area_score
            category_count += 1
        
        # Calculate the average score (sum divided by the number of selected categories)
        if category_count > 0:
            average_score = score_sum / category_count
            clinician_scores[clinician] = round(average_score, 2)
    
    # Sort clinicians by their scores in descending order
    ranked_clinicians = sorted(clinician_scores.items(), key=lambda x: x[1], reverse=True)
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

@app.route('/match', methods=['POST'])
def match():
    selected_area = request.form['area']
    selected_age = request.form['age']
    selected_intervention = request.form['intervention']
    selected_work_area = request.form['work_area']

    # Load data and calculate clinician ratings
    df, area_of_practice, age_client_type, interventions, areas_of_work, clinicians = load_excel_data()
    ranked_clinicians = calculate_ratings(df, selected_area, selected_age, selected_intervention, selected_work_area, clinicians)

    return render_template('match.html', 
                           area=selected_area, 
                           age=selected_age, 
                           intervention=selected_intervention, 
                           work_area=selected_work_area,
                           ranked_clinicians=ranked_clinicians)

if __name__ == '__main__':
    app.run(debug=True)