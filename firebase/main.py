import os
from typing import Final, Union, TypedDict

import firebase_admin
from firebase_admin import credentials, firestore

CommuterPassType = TypedDict('CommuterPassType', {
    'starting_point': str,
    'end_point': str
})

COLLECTION_NAME: Final[str] = 'user_preferences'


class Firebase:

    def __init__(self, cred_path: str = './firebase/cred.json') -> None:
        # firebaseの初期化
        if not os.path.isfile(cred_path):
            with open(cred_path, 'w') as f:
                f.write(os.getenv('FIREBASE_CRED_JSON', None))
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

        # firestoreの初期化
        self.db = firestore.client()

    def post_user_commuter_pass(self, user_id: str, commuter_pass: CommuterPassType) -> None:
        user_preference = {
            'user_id': user_id,
            'commuter_pass': commuter_pass
        }
        self.db.collection(COLLECTION_NAME).document(user_id).set(user_preference)

    def get_user_commuter_pass(self, user_id: str) -> Union[CommuterPassType, str]:
        response = self.db.collection(COLLECTION_NAME).document(user_id).get()
        if response.exists:
            return response.to_dict()['commuter_pass']
        else:
            return 'Not Found'
