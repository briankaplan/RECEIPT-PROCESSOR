#!/usr/bin/env python3
"""
Convert token JSON files to pickle files
"""

import os
import json
import pickle
from google.oauth2.credentials import Credentials

def create_pickle_file(token_json, output_path):
    """Convert a token JSON string to a pickle file"""
    try:
        # Parse the JSON string
        token_data = json.loads(token_json)
        
        # Create Credentials object
        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
            scopes=token_data["scopes"]
        )
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save as pickle
        with open(output_path, "wb") as f:
            pickle.dump(creds, f)
            
        print(f"✅ Created {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error creating {output_path}: {e}")
        return False

def main():
    # Token data for each account
    tokens = {
        "kaplan_brian_at_gmail_com.pickle": "{\"token\": \"ya29.a0AW4XtxgReRmFgGM8fzeIWFlRmZO3HIqwXA4IEmtdrNsu-70BU-lOjpiaTnYWGizolBXjA0wez6zofb6HMH2uethQOcCtqN2zsEa3O86BmZ27GImTm66XtcffhBeAVkX2G6vltaCtMqFQaS4QvAR1vbG3Mcrn_rAMby4PnglZaCgYKAZ8SARUSFQHGX2Mi1RAGulBF0sY7h1n4cYWUrA0175\", \"refresh_token\": \"1//01fjEiSnoXy0HCgYIARAAGAESNwF-L9Ir245d2KD39Orqhou70ZfgfBHL9jZf7sjF2nk3eU4j5dJeTuM4epVWKacp7o_Wy_WhUOc\", \"token_uri\": \"https://oauth2.googleapis.com/token\", \"client_id\": \"409487441168-f6knaetqq9f5s960lvbujkps75op2et3.apps.googleusercontent.com\", \"client_secret\": \"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\", \"scopes\": [\"https://mail.google.com/\", \"https://www.googleapis.com/auth/gmail.readonly\", \"https://www.googleapis.com/auth/gmail.modify\", \"https://www.googleapis.com/auth/drive\", \"https://www.googleapis.com/auth/drive.file\", \"https://www.googleapis.com/auth/spreadsheets\", \"https://www.googleapis.com/auth/photoslibrary.readonly\"], \"universe_domain\": \"googleapis.com\", \"account\": \"\", \"expiry\": \"2025-06-09T21:15:27.297786Z\"}",
        
        "brian_at_downhome_com.pickle": "{\"token\": \"ya29.A0AW4XtxgDMRPtYAK1-zQcc2g8-IMzAy7vhte6rpMKaSi3oMFUOEr5RLKjfeffjoFgaSJDY_1ZZRCurewFtxcW8Hp-_ZGyG0WNZTxi-gP6FkYKoDjXMW4l6sV5pTkdR38OlUHNAXWDhWMviLnmYFMRzFdA9ksURAxNrvRdAUKVwb_vvugTp5sc1uiT1F-GiRAtCbsEx8oaCgYKAV0SARYSFQHGX2MiOvED-FJS63LchLGVZxb62Q0206\", \"refresh_token\": \"1//01EYCnDf4sbE1CgYIARAAGAESNwF-L9IrC1geynYtg6EWccxtc3OlcEQDfbenps82clFx95U1-kb2HQ9X9SmIiWtTs9TFfOy_qQg\", \"token_uri\": \"https://oauth2.googleapis.com/token\", \"client_id\": \"616745095508-nohpqpnh5c251ccmncpd7eej3nefu6kq.apps.googleusercontent.com\", \"client_secret\": \"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\", \"scopes\": [\"https://mail.google.com/\", \"https://www.googleapis.com/auth/gmail.readonly\", \"https://www.googleapis.com/auth/gmail.modify\", \"https://www.googleapis.com/auth/drive\", \"https://www.googleapis.com/auth/drive.file\", \"https://www.googleapis.com/auth/spreadsheets\", \"https://www.googleapis.com/auth/photoslibrary.readonly\"], \"universe_domain\": \"googleapis.com\", \"account\": \"\", \"expiry\": \"2025-06-09T21:15:34.429767Z\"}",
        
        "brian_at_musiccityrodeo_com.pickle": "{\"token\": \"ya29.a0AW4XtxjPeu5tiKKhWCkIUgQCN3Pk0TQqtNQ7sAT5s8SyAf4mh6grpoDwrvr6JTz2G1bLDEXLW1m6lStMY8ckOurpkMIl-sjafYJB-4ORmVbfVNTaBTS3WYUftPeDvXbt_baCpzIJnAf13X40woeDPdLptWkNOaOIhX5m-UU2aCgYKAb0SARQSFQHGX2MiDfE44be7ObFIImPXOatOBw0175\", \"refresh_token\": \"1//01ZNArNEvnARrCgYIARAAGAESNwF-L9IrPBIB3rs4w7DierWR_Be4TQIJ0mWUL9b6obKVCYIVkBswLK4tk_tHVxOu5tBr-varXjs\", \"token_uri\": \"https://oauth2.googleapis.com/token\", \"client_id\": \"576938328901-svmliarlv4dqdnnl2a0tr3kq9skleigt.apps.googleusercontent.com\", \"client_secret\": \"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\", \"scopes\": [\"https://mail.google.com/\", \"https://www.googleapis.com/auth/gmail.readonly\", \"https://www.googleapis.com/auth/gmail.modify\", \"https://www.googleapis.com/auth/drive\", \"https://www.googleapis.com/auth/drive.file\", \"https://www.googleapis.com/auth/spreadsheets\", \"https://www.googleapis.com/auth/photoslibrary.readonly\"], \"universe_domain\": \"googleapis.com\", \"account\": \"\", \"expiry\": \"2025-06-09T21:15:39.774372Z\"}"
    }
    
    # Create pickle files
    success_count = 0
    for filename, token_json in tokens.items():
        output_path = os.path.join("gmail_tokens", filename)
        if create_pickle_file(token_json, output_path):
            success_count += 1
    
    print(f"\n✅ Created {success_count}/{len(tokens)} pickle files")

if __name__ == "__main__":
    main() 