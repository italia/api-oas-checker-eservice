"""
Azure Function: ProcessValidation
Triggers on HTTP POST request to process OpenAPI validation.
"""

import logging
import json
import azure.functions as func

# Import from shared package
try:
    from shared.validator import validate_openapi
    from shared.utils import json_dumps
    from shared.security import generate_hmac_headers
    from shared.http_client import get_http_client
except ImportError:
    # Fallback for local development or different folder structures
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    from shared.validator import validate_openapi
    from shared.utils import json_dumps
    from shared.security import generate_hmac_headers
    from shared.http_client import get_http_client

logger = logging.getLogger(__name__)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function entry point.
    Processes OpenAPI validation request using content from request body.
    """
    logger.info('ProcessValidation function triggered.')

    try:
        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return _problem_response("Invalid JSON in request body", 400)

        validation_id = req_body.get('validation_id')
        file_content = req_body.get('file_content')
        callback_url = req_body.get('callback_url')
        
        # Optional fields
        ruleset_name = req_body.get('ruleset_name', 'default')
        ruleset_content = req_body.get('ruleset_content', '')
        errors_only = req_body.get('errors_only', False)

        if not all([validation_id, file_content, callback_url]):
            missing = [f for f in ['validation_id', 'file_content', 'callback_url'] if not req_body.get(f)]
            return _problem_response(f"Missing required fields: {', '.join(missing)}", 400)

        logger.info(f"Processing validation {validation_id} for ruleset {ruleset_name}")

        try:
            # 1. Run Validation
            report = validate_openapi(
                content=file_content,
                ruleset_name=ruleset_name,
                ruleset_content=ruleset_content,
                errors_only=errors_only
            )

            # 2. Prepare Callback
            callback_data = {
                "validation_id": validation_id,
                "status": "COMPLETED",
                "report_content": report
            }
            
            # Serialize payload consistently for HMAC
            payload_str = json_dumps(callback_data)
            headers = generate_hmac_headers(payload_str)
            headers["Content-Type"] = "application/json"

            # 3. Send Callback
            logger.info(f"Sending callback to {callback_url}")
            client = get_http_client()
            response = await client.post(
                callback_url, 
                content=payload_str, 
                headers=headers
            )
            logger.info(f"Callback status: {response.status_code}")

            return func.HttpResponse(
                json_dumps({
                    "validation_id": validation_id,
                    "status": "success",
                    "message": "Validation completed and callback initiated"
                }),
                status_code=200,
                mimetype="application/json"
            )

        except Exception as e:
            logger.error(f"Error during validation process: {str(e)}", exc_info=True)
            await _notify_failure(validation_id, callback_url, str(e))
            return _problem_response(f"Internal error during validation: {str(e)}", 500)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return _problem_response(str(e), 500)


async def _notify_failure(validation_id: str, callback_url: str, error_message: str):
    """Notify callback URL about validation failure"""
    if not callback_url:
        return

    try:
        callback_data = {
            "validation_id": validation_id,
            "status": "FAILED",
            "error_message": error_message
        }
        payload_str = json_dumps(callback_data)
        headers = generate_hmac_headers(payload_str)
        headers["Content-Type"] = "application/json"
        
        client = get_http_client()
        await client.post(
            callback_url, 
            content=payload_str, 
            headers=headers
        )
    except Exception as callback_error:
        logger.error(f"Failed to send failure callback: {str(callback_error)}")


def _problem_response(detail: str, status_code: int) -> func.HttpResponse:
    """Return a RFC 7807 problem detail response"""
    return func.HttpResponse(
        json_dumps({
            "type": "about:blank",
            "title": "Error" if status_code >= 500 else "Bad Request",
            "status": status_code,
            "detail": detail
        }),
        status_code=status_code,
        mimetype="application/problem+json"
    )