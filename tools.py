import hubscape_adk
import uuid

def show_contact_form() -> str:
    """Displays the contact request form widget to the user to collect their details."""
    try:
        context = hubscape_adk.get_context()
        context.show_widget(widget_template_id="contact_form")
        return "Displaying contact form."
    except Exception as e:
        return f"Error displaying contact form: {str(e)}"

def save_contact(name: str, email: str, description: str) -> dict:
    """Saves a contact/help request form submission to the hub's agent data in Firestore.

    Args:
        name: The name of the user requesting help.
        email: The email address of the user.
        description: The description of the help needed.
    """
    try:
        context = hubscape_adk.get_context()
        doc_id = f"contact_{uuid.uuid4().hex[:8]}"
        
        # Save to Firestore in hub scope
        context.save(
            scope="hub",
            collection_name="contact_requests",
            doc_id=doc_id,
            data={
                "name": name,
                "email": email,
                "description": description,
                "status": "pending"
            }
        )
        return {"status": "success", "message": "Contact request saved successfully."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save request: {str(e)}"}
