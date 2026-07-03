import requests

def test_saving_profile():
    base_url = 'http://127.0.0.1:5001/api'
    
    # 1. Register
    requests.post(f"{base_url}/auth/register", json={
        "username": "testuser2",
        "email": "test2@test.com",
        "password": "password"
    })
    
    # 2. Login
    res = requests.post(f"{base_url}/auth/login", json={
        "username": "testuser2",
        "password": "password"
    })
    token = res.json().get('access_token')
    if not token:
        print("Login failed:", res.text)
        return
        
    print("Logged in, token:", token)
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Save profile - skin
    data_skin = {
        "skin_type": "oily", "sensitivity_level": "low", "skin_tone": "fair",
        "skin_concerns": "acne", "acne_level": "none", "pigmentation_level": "none",
        "pore_size": "small", "under_eye_issue": "none", "lip_condition": "normal",
        "seasonal_skin_changes": "none"
    }
    res = requests.post(f"{base_url}/profile/skin", json=data_skin, headers=headers)
    print("Skin:", res.status_code, res.text)
    
    # 4. Save profile - lifestyle
    data_lifestyle = {
        "sleep_hours": 8, "stress_level": "low", "exercise_frequency": "none",
        "screen_time": "low", "sunscreen_usage": "never", "face_washing_frequency": "1",
        "makeup_usage": "never", "pollution_exposure": "low", "occupation_type": "indoor"
    }
    res = requests.post(f"{base_url}/profile/lifestyle", json=data_lifestyle, headers=headers)
    print("Lifestyle:", res.status_code, res.text)
    
    # 5. Save profile - allergy
    data_allergy = {
        "has_known_allergy": "yes", "allergy_type": "food", "reactive_ingredients": "peanut",
        "reaction_symptoms": "redness", "reaction_severity": "mild", "visited_dermatologist": "no",
        "taking_medication": "no", "additional_allergy_info": "none"
    }
    res = requests.post(f"{base_url}/profile/allergy", json=data_allergy, headers=headers)
    print("Allergy:", res.status_code, res.text)
    
    # 6. Save profile - diet
    data_diet = {
        "water_intake_liters": 2.5, "sugar_consumption": "Moderate", "fruits_veggies_intake": "None",
        "fast_food_freq": "Rarely", "alcohol_smoking": "Neither", "tea_coffee_intake": "None"
    }
    res = requests.post(f"{base_url}/profile/diet", json=data_diet, headers=headers)
    print("Diet:", res.status_code, res.text)

if __name__ == '__main__':
    test_saving_profile()
