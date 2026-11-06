
from .models import TicketAnalysis


def analyze_ticket(ticket):

    ticket_text = f"{ticket.title} {ticket.description}".lower()

    # Identify the most relevant department
    category_keywords = {
        'Information Technology': [
            'computer', 'laptop', 'software', 'network',
            'internet', 'server', 'system', 'login', 'password'
        ],
        'Finance': [
            'payment', 'refund', 'invoice', 'salary',
            'billing', 'transaction', 'money'
        ],
        'Human Resources': [
            'leave', 'attendance', 'employee', 'payroll',
            'recruitment', 'holiday'
        ],
        'Operations': [
            'maintenance', 'equipment', 'office',
            'facility', 'electricity', 'power'
        ],
        'Customer Support': [
            'customer', 'service', 'complaint',
            'support', 'help', 'request'
        ]
    }

    predicted_category = 'Customer Support'

    for category, keywords in category_keywords.items():
        if any(word in ticket_text for word in keywords):
            predicted_category = category
            break

    # Predict ticket priority
    critical_words = ['urgent', 'critical', 'emergency', 'security breach']
    high_words = ['not working', 'server down', 'system failure', 'blocked']
    low_words = ['general enquiry', 'suggestion', 'minor issue']

    if any(word in ticket_text for word in critical_words):
        predicted_priority = 'Critical'
    elif any(word in ticket_text for word in high_words):
        predicted_priority = 'High'
    elif any(word in ticket_text for word in low_words):
        predicted_priority = 'Low'
    else:
        predicted_priority = 'Medium'

    # Detect customer sentiment
    negative_words = [
        'angry', 'frustrated', 'disappointed',
        'terrible', 'poor', 'worst', 'problem'
    ]

    positive_words = [
        'thank you', 'excellent', 'great',
        'happy', 'good', 'appreciate'
    ]

    if any(word in ticket_text for word in negative_words):
        sentiment = 'Negative'
    elif any(word in ticket_text for word in positive_words):
        sentiment = 'Positive'
    else:
        sentiment = 'Neutral'

    # Initial heuristic score, not a calibrated ML confidence
    confidence_score = 0.80

    if predicted_priority == 'Critical':
        confidence_score = 0.90

    # Generate a suggested response
    if sentiment == 'Negative':
        suggested_response = (
            "We apologize for the inconvenience. "
            "Our support team will investigate this issue "
            "and work towards resolving it as soon as possible."
        )
    else:
        suggested_response = (
            "Thank you for contacting SmartDesk. "
            "Your request has been received and assigned "
            "to the relevant team for further assistance."
        )

    # Save or update the existing analysis
    analysis, created = TicketAnalysis.objects.update_or_create(
        ticket=ticket,
        defaults={
            'predicted_category': predicted_category,
            'predicted_priority': predicted_priority,
            'sentiment': sentiment,
            'confidence_score': confidence_score,
            'suggested_response': suggested_response
        }
    )

    return analysis
