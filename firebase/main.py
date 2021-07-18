from typing import Final, TypedDict

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
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)

        # firestoreの初期化
        self.db = firestore.client()

    def post_user_commuter_pass(self, user_id: str, commuter_pass: CommuterPassType) -> None:
        user_preference = {
            'user_id': user_id,
            'commuter_pass': commuter_pass
        }
        self.db.collection(COLLECTION_NAME).add(user_preference)

    def get_user_commuter_pass(self, user_id: str) -> CommuterPassType:
        response = self.db.collection(COLLECTION_NAME).where('user_id', '==', user_id).stream()
        for user_preference in response:
            commuter_pass: CommuterPassType = user_preference.to_dict()['commuter_pass']
            break
        return commuter_pass
