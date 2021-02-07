import requests


def post_and_print_info_and_confirm_success(response_url, text):
    r = requests.post(
        url=response_url,
        json={
            'text': text
        },
        headers={
            'Content-Type': "application/json"
        }
    )
    if r.status_code != 200:
        print(r.status_code, r.reason)
        print(r.text)
        raise Exception("requests.post failed")
    return r


def build_response(res):
    return {
        'statusCode': "200",
        'body': res,
        'headers': {
            'Content-Type': "application/json",
        }
    }
