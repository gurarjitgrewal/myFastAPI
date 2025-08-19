import random
import datetime
from sklearn.linear_model import SGDClassifier
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import accuracy_score




class SimpleEmailData:
    """Generates fake emails with evolving spam tactics"""

    def __init__(self):
        self.spam_words = ['win', 'free', 'money', 'click', 'buy']
        self.normal_words = ['meeting', 'project', 'report', 'team', 'work']

    def generate_email(self, day=0):
        if day > 20:
            new_spam_words = ['prize', 'offer', 'deal', 'sale', 'discount']
            all_spam_words = self.spam_words + new_spam_words
        else:
            all_spam_words = self.spam_words

        is_spam = random.random() < 0.3
        if is_spam:
            num_words = random.randint(3, 8)
            words = random.choices(all_spam_words, k=num_words)
            words += random.choices(self.normal_words, k=2)
        else:
            num_words = random.randint(4, 10)
            words = random.choices(self.normal_words, k=num_words)

        return ' '.join(words), (1 if is_spam else 0)


class DynamicSpamDetector:
    """Spam detector with dynamic vocabulary and retraining"""
    def __init__(self):
        self.vectorizer = CountVectorizer(max_features=50)
        self.model = SGDClassifier(loss='log_loss', random_state=42)
        self.is_trained = False
        self.all_emails = []
        self.all_labels = []
        self.last_trained = None
        self.history = []

    def retrain_with_all_data(self):
        if not self.all_emails:
            return
        email_features = self.vectorizer.fit_transform(self.all_emails)
        self.model = SGDClassifier(loss='log_loss', random_state=42)
        self.model.fit(email_features, self.all_labels)
        self.is_trained = True
        self.last_trained = datetime.datetime.now()

    def initial_training(self, emails, labels):
        self.all_emails.extend(emails)
        self.all_labels.extend(labels)
        self.retrain_with_all_data()

    def predict_email(self, email_text):
        if not self.is_trained:
            return 0, 0.5
        email_features = self.vectorizer.transform([email_text])
        prediction = self.model.predict(email_features)[0]
        confidence = max(self.model.predict_proba(email_features)[0])
        return int(prediction), float(confidence)

    def learn_from_new_email(self, email_text, true_label):
        self.all_emails.append(email_text)
        self.all_labels.append(true_label)
        self.retrain_with_all_data()

    def evaluate(self, emails, labels):
        preds = [self.predict_email(e)[0] for e in emails]
        return accuracy_score(labels, preds)
