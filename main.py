import subprocess

subprocess.call(["clear"])

from requests import get, post

from json import dumps, loads
import urllib3

urllib3.disable_warnings()
from subprocess import PIPE, Popen
from os.path import exists
from os import mkdir, getenv
import argparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

class Colors:
    HEADER = '\033[95m'
    OK = '\033[94m'
    FAIL = '\033[91m'
    SUCCESS = '\033[92m'
    RESET = '\033[0m'
    WARNING = '\033[93m'
    BOLD = '\033[1m'


class HaxUnit:
    yes_answers = ("y", "yes", "ye")

    acunetix_email = acunetix_password = ""

    all_subdomains = []
    all_subdomains_up = []
    timestamp = datetime.now()

    def __init__(self, site, mode, verbose, python_bin, dir_path, iserver, itoken, acu_session, yes_to_all, update,
                 install_all, resolvers_file, wpscan_api_token):
        self.site = site
        self.verbose = verbose
        self.quick = True if mode == "quick" else False
        self.python_bin = python_bin
        self.dir_path = dir_path
        self.yes_to_all = yes_to_all
        self.update = update
        self.install_all = install_all
        self.resolvers_file = resolvers_file
        self.wpscan_api_token = wpscan_api_token or getenv("WPSCAN_API_KEY")
        self.acunetix_threshold = int(getenv("ACUNETIX_THRESHOLD", 30))

        self.iserver = iserver
        self.itoken = itoken

        self.acu_session = acu_session or getenv("ACUNETIX_API_KEY")

        self.cmd("clear")

        print(Colors.BOLD)
        print("""                                                                         
  _    _            _    _       _ _   
 | |  | |          | |  | |     (_) |  
 | |__| | __ ___  _| |  | |_ __  _| |_ 
 |  __  |/ _` \ \/ / |  | | '_ \| | __|
 | |  | | (_| |>  <| |__| | | | | | |_ 
 |_|  |_|\__,_/_/\_\\____/|_| |_|_|\__|

                                       v3.4 by the butcher""")

        print()

        if self.install_all:
            self.install_all_tools()
            self.print("Init", "All tools are successfully installed - good luck!", Colors.SUCCESS)
            exit()
        elif not self.site:
            self.print("Init", "Please pass a domain (-d)", Colors.FAIL)
            exit()

        print("\n[HaxUnit] Target:", site)
        print(Colors.RESET)

    @staticmethod
    def print(title: str = "", text: str = "", color_type="") -> None:
        print(f"[{Colors.BOLD}HaxUnit{Colors.RESET}] [{Colors.OK}{title}{Colors.RESET}] {color_type}{text}{Colors.RESET}")

    def cmd(self, cmd: str) -> str:
        cmd = " ".join(cmd.split())
        if self.verbose:
            self.print("CMD", cmd)
        subprocess_cmd = Popen(
            cmd,
            shell=True,
            stdout=PIPE
        )
        subprocess_return = subprocess_cmd.stdout.read().decode("utf-8").strip()
        if subprocess_return:
            print(subprocess_return)
        return subprocess_return

    def ask(self, question: str) -> bool:
        if self.yes_to_all:
            return True
        return True if input(question).lower() in self.yes_answers else False

    def read(self, file_name: str, text: bool = False) -> (str, list):
        try:
            if text:
                return "\n".join(list(set([_.strip() for _ in open(f"{self.dir_path}/{file_name}", "r").readlines()])))
            else:
                return list(set([_.strip() for _ in open(f"{self.dir_path}/{file_name}", "r").readlines()]))
        except FileNotFoundError:
            if text:
                return "FileNotFoundError"
            else:
                return []

    def write_subdomains(self, mode="a") -> None:
        with open(f"{self.dir_path}/all_subdomains.txt", mode) as f:
            all_subdomains_text = "\n".join([_ for _ in list(set(self.all_subdomains)) if _])
            f.write(all_subdomains_text)

    def nrich(self) -> None:
        self.cmd(f"nrich {self.dir_path}/dnsx_ips.txt > {self.dir_path}/nrich_result.txt")

    def httpx(self) -> None:
        self.cmd(f"httpx -l {self.dir_path}/all_subdomains.txt {'' if self.verbose else '-silent'} -o {self.dir_path}/httpx_result.csv -td -cdn -csv -timeout 15")

        awk_cmd_2 = """awk -F "," {'print $9'} | awk -F ":" {'print $1 ":" $2'} """
        self.cmd(f"cat {self.dir_path}/httpx_result.csv | {awk_cmd_2} | tail -n +2 | sort -u > {self.dir_path}/all_subdomains_up.txt")

        awk_cmd_3 = """awk -F "," {'print $18'}"""
        self.cmd(f"cat {self.dir_path}/httpx_result.csv | {awk_cmd_3} | sort -u | head -n -1 >> {self.dir_path}/httpx_ips.txt")

        self.cmd(f"cat {self.dir_path}/httpx_ips.txt {self.dir_path}/dnscan_ips.txt | sort -u > {self.dir_path}/all_ips.txt")

        self.all_subdomains_up = self.remove_unwanted_domains(self.read("all_subdomains_up.txt"))

    def naabu(self) -> None:
        input_file = self.read("all_subdomains.txt")

        if not input_file:
            self.print("Naabu", "all_subdomains.txt is empty - skipping")
        else:
            self.cmd(f"""
                sudo naabu -l {self.dir_path}/dnsx_ips.txt
                 -c 100 {'' if self.verbose else '-silent'}
                 -no-color
                 -exclude-cdn
                 -p 80,81,300,443,591,593,832,981,1010,1311,2082,2087,2095,2096,2480,3000,3128,3333,4243,4567,4711,4712,4993,5000,5104,5108,5800,6543,7000,7396,7474,8000,8001,8008,8014,8042,8069,8080,8081,8088,8090,8091,8118,8123,8172,8222,8243,8280,8281,8333,8443,8500,8834,8880,8888,8983,9000,9043,9060,9080,9090,9091,9200,9443,9800,9943,9980,9981,12443,16080,18091,18092,20720,28017
                 -o {self.dir_path}/naabu_portscan.txt
            """)

            self.ask_to_add(self.read("naabu_portscan.txt"))
            self.write_subdomains("w")

    def subfinder(self) -> None:
        self.print("Subfinder", "Process started")
        self.cmd(f"subfinder -d {self.site} {'' if self.verbose else '-silent'} -t 100 -nW -nC -all -o {self.dir_path}/subfinder_subdomains.txt")
        self.ask_to_add(self.read("subfinder_subdomains.txt"))

    def findomain(self) -> None:
        pass

    def nuclei(self) -> None:
        self.cmd(f"""nuclei -l {self.dir_path}/all_subdomains_up.txt
                        -t templates
                        {"-stats -metrics" if self.verbose else "-silent "} 
                        -o {self.dir_path}/nuclei_result.txt
                        -bulk-size 100
                        -c 100
                        {'-severity high,critical' if self.quick else ""} 
                        -no-timestamp
                        {f"-interactsh-url {self.iserver}" if self.iserver else ""}
                        {f"-itoken {self.itoken}" if self.itoken else ""}
                    """)

    def check_ip(self) -> None:
        ipaddress = get("http://ifconfig.me/ip").text

        ip_check = get(f"https://blackbox.ipinfo.app/lookup/{ipaddress}").text

        if ip_check != "Y":
            if self.ask(f"{Colors.WARNING}(!) Your IP ({ipaddress}) does not seem to be a proxy or VPN, would you like to quit? {Colors.RESET}"):
                exit()

    @staticmethod
    def remove_unwanted_domains(domain_list) -> list:
        unwanted_domains = (
            "cloudfront.net",
            "googleusercontent.com",
            "akamaitechnologies.com",
            "amazonaws.com",
            "salesforce-communities.com",
            "cloudflaressl.com",
            "cloudflare.net",
            "cloudflare.com",
            "transip.nl",
            "transip.eu",
            "transip.net",
            "azure-dns.com",
            "azure-dns.org",
            "azure-dns.net",
        )

        return [_ for _ in domain_list if (not _.endswith(unwanted_domains) and not _.startswith("*"))]

    def ask_to_add(self, ask_domains: list, reask_same_tld=False) -> bool:
        ask_domains = [domain for domain in list(set(ask_domains)) if domain not in self.all_subdomains]
        ask_domains = self.remove_unwanted_domains(ask_domains)

        if ask_domains:
            print()
            for d in ask_domains:
                print(d)
            print()

            if self.ask(f"\nWould you like to add {len(ask_domains)} domains to the list? "):
                self.all_subdomains.extend(ask_domains)
                self.write_subdomains()
                return True
            elif reask_same_tld:
                self.ask_to_add(list(set([_ for _ in ask_domains if _.endswith(self.site)])))
                return True
        return False

    def sonar_search(self) -> None:
        self.print("Sonar search", "Process started")

        try:
            domain_name = self.site.split(".")[0]

            all_sonar_subdomains = []

            sonar_domains = get(f"https://sonar.omnisint.io/tlds/{domain_name}", timeout=15).json()

            for domain in sonar_domains:
                sonar_subdomains = get(f"https://sonar.omnisint.io/subdomains/{domain}", timeout=15).text.strip()
                if sonar_subdomains != "null":
                    all_sonar_subdomains.extend(loads(sonar_subdomains))

            self.ask_to_add(all_sonar_subdomains, reask_same_tld=True)
        except:# (ConnectionError, TimeoutError):
            self.print("Sonar search", "Sonar search failed - skipping", Colors.FAIL)

    def sonar_reverse_dns(self) -> None:
        self.print("Sonar reverse DNS", "Sonar reverse dns started")

        dnsx_ips = self.read("dnsx_ips.txt")

        use_whole_range = self.ask("Do you want to scan /32 range for all IP addresses (x.x.x.0/32)? ")

        self.domain_name_no_tld = self.site.split(".")[0]

        for ip_address in dnsx_ips:
            try:

                domain_ip_split = ip_address.split(".")
                domain_ip_range = f"{domain_ip_split[0]}.{domain_ip_split[1]}.{domain_ip_split[2]}.0/32"

                self.print("Sonar reverse DNS", f"Domain IP: {ip_address}\n")

                reverse_dns_domains = get(f"https://sonar.omnisint.io/reverse/{domain_ip_range if use_whole_range else ip_address}").json()
                if reverse_dns_domains:
                    if use_whole_range:
                        all_domains = []
                        for ip in reverse_dns_domains:
                            all_domains.extend(reverse_dns_domains[ip])
                        reverse_dns_domains = list(set(all_domains))

                    reverse_dns_domains = self.remove_unwanted_domains(reverse_dns_domains)

                    if not self.ask_to_add(reverse_dns_domains):
                        containing_domain = list(set([_ for _ in reverse_dns_domains if self.domain_name_no_tld in _]))

                        if containing_domain:
                            print()
                            for d in containing_domain:
                                print(d)

                            self.ask_to_add(containing_domain)
            except:# (ConnectionError, TimeoutError):
                self.print("Sonar reverse DNS", "Sonar reverse dns failed - skipping", Colors.FAIL)

    def dnsx_subdomains(self) -> None:
        self.print("DNSx", "Started subdomain bruteforce")
        self.cmd(f"dnsx -silent -d {self.site} -w data/subdomains-10000.txt -wd {self.site} -o {self.dir_path}/dnsx_result.txt {f'-r {self.resolvers_file}' if self.resolvers_file else ''}")
        self.ask_to_add(self.read("dnsx_result.txt"))

        if self.ask("\nWould you like to continue recursively bruteforce the found subdomains? "):
            self.print("DNSx", "Started multi-threaded recursive bruteforce")

            all_found_subdomains = []

            try:
                for iteration in range(0, 100):
                    print()
                    self.print("DNSx", f"Iteration: {iteration}")

                    def dnsx_brute(subdomain):
                        self.cmd(f"dnsx -silent -d {subdomain} -w data/subdomains-1000.txt -wd {self.site} -o {self.dir_path}/dnsx_recursive_iter_{iteration}_result.txt {f'-r {self.resolvers_file}' if self.resolvers_file else ''}")

                    file_to_read = "dnsx_result.txt" if not iteration else f"dnsx_recursive_iter_{iteration - 1}_result.txt"
                    self.print("DNSx", f"Reading file: {file_to_read}")

                    dnsx_result = self.read(file_to_read)
                    self.print("DNSx", f"List of subdomains: {dnsx_result}")

                    if dnsx_result:
                        all_found_subdomains.extend(dnsx_result)
                        with ThreadPoolExecutor(max_workers=5) as pool:
                            pool.map(dnsx_brute, dnsx_result)
                    else:
                        break
            except KeyboardInterrupt:
                self.print("DNSx", "Bruteforce stopped")

            self.ask_to_add(all_found_subdomains)

    def dnsx_ips(self) -> None:
        self.print("DNSx", "Get A records")
        self.cmd(f"dnsx -l {self.dir_path}/all_subdomains.txt -silent -a -resp-only -silent | sort -u > {self.dir_path}/dnsx_ips.txt")

        self.ask_to_add(self.read("dnsx_result.txt"))

    def install_acunetix(self) -> None:
        if not exists("acunetix_docker"):
            self.print("Acunetix", "Installing Acunetix Docker")

            self.cmd("git clone https://github.com/Bandit-HaxUnit/acu807155 acunetix_docker")

            new_email = input("\n\nPlease enter acunetix email (leave blank for default: contact@manhtuong.net): ")
            if new_email:
                self.cmd(f"sed -i 's/contact@manhtuong.net/{new_email}/g' acunetix_docker/Dockerfile")
                self.acunetix_email = new_email

            new_password = input("\nPlease enter acunetix password (leave blank for default: Abcd1234): ")
            if new_password:
                self.cmd(f"sed -i 's/Abcd1234/{new_password}/g' acunetix_docker/Dockerfile")
                self.acunetix_password = new_password

            self.cmd("docker build -t aws acunetix_docker")
            self.cmd("docker run -it -d -p 3443:3443 aws")

            self.print("Acunetix", "Installed successfully - available at https://localhost:3443/", Colors.SUCCESS)

    def acunetix(self) -> None:

        def acunetix_up():
            try:
                get("https://localhost:3443/api/v1/target_groups")
                return True
            except ConnectionError:
                return False

        if self.acu_session and acunetix_up():
            self.print("Acunetix", "Starting acunetix")

            data = {}
            cookies = {'ui_session': self.acu_session}
            headers = {'x-auth': self.acu_session, 'Content-Type': 'application/json'}

            print()
            for d in self.all_subdomains_up:
                print(d)
            print()

            self.print("Acunetix", f"Active subdomain count: {len(self.all_subdomains_up)}")

            all_groups = get("https://localhost:3443/api/v1/target_groups", headers=headers, verify=False).json()["groups"]

            try:
                group_id = next(row["group_id"] for row in all_groups if row["name"] == self.site)
            except StopIteration:
                group_id = None

            if group_id:
                self.print("Acunetix", f"Group already exists: {group_id}")
            else:
                self.print("Acunetix", "Creating new group")

                group_id = post(
                    'https://localhost:3443/api/v1/target_groups',
                    headers=headers,
                    cookies=cookies,
                    data=dumps({"name": self.site, "description": ""}),
                    verify=False
                ).json()["group_id"]

            if len(self.all_subdomains_up) < self.acunetix_threshold and self.ask(
                    "[HaxUnit] Do you want to scan all subdomains using acunetix? "):
                data = {
                    "targets": [{
                        "address": subdomain,
                        "description": ""
                    } for subdomain in self.all_subdomains_up],
                    "groups": [group_id]
                }
            elif self.ask("[HaxUnit] Do you want to scan only the main domain using acunetix? "):
                main_domain = [_ for _ in self.all_subdomains_up if f"//{self.site}" in _][0]
                self.print("Acunetix", f"Main domain: {main_domain}")
                data = {
                    "targets": [{
                        "address": main_domain,
                        "description": ""
                    }],
                    "groups": [group_id]
                }

            if data:

                response = post('https://localhost:3443/api/v1/targets/add', headers=headers, cookies=cookies,
                                data=dumps(data), verify=False).json()

                for target in response["targets"]:
                    data = {
                        "profile_id": "11111111-1111-1111-1111-111111111111",
                        "ui_session_id": "56eeaf221a345258421fd6ae1acca394",
                        "incremental": False,
                        "schedule": {
                            "disable": False,
                            "start_date": None,
                            "time_sensitive": False
                        },
                        "target_id": target["target_id"]
                    }

                    post('https://localhost:3443/api/v1/scans', headers=headers, cookies=cookies, data=dumps(data),
                         verify=False)

                self.print("Acunetix", f"Scan(s) started!")

    def gau_unfurl(self) -> None:
        self.cmd(f"cat {self.dir_path}/all_subdomains.txt | getau | unfurl --unique domains > {self.dir_path}/gau_unfurl_domains.txt")
        self.ask_to_add(self.read("gau_unfurl_domains.txt"))

    def ripgen(self):
        self.cmd(f"ripgen -d {self.dir_path}/all_subdomains.txt | sort -u | dnsx -silent > {self.dir_path}/ripgen_result.txt")
        self.ask_to_add(self.read("ripgen_result.txt"))

    def wpscan(self):

        def single_wpscan(wp_domain):
            filename = wp_domain.replace("https://", "").replace("http://", "").replace(".", "_").replace("/", "").replace(":", "_").strip()
            self.cmd(f"docker run -it --rm wpscanteam/wpscan --url {wp_domain} {f'--api-token {self.wpscan_api_token}' if self.wpscan_api_token else ''} --ignore-main-redirect >> {self.dir_path}/wpscan_{filename}.txt")

        self.cmd(f"grep -i wordpress {self.dir_path}/httpx_result.csv | awk -F ',' {{'print $9'}} | sort -u > {self.dir_path}/wordpress_domains.txt")
        wordpress_domains = self.read("wordpress_domains.txt")

        if wordpress_domains:
            for domain in wordpress_domains:
                print(domain)
            print()

            if self.ask(f"Would you like to run wpscan on all ({len(wordpress_domains)}) domains? "):

                with ThreadPoolExecutor(max_workers=5) as pool:
                    pool.map(single_wpscan, wordpress_domains)

    def install_nrich(self) -> None:
        for cmd in (
                "wget https://gitlab.com/api/v4/projects/33695681/packages/generic/nrich/latest/nrich_latest_amd64.deb",
                "sudo dpkg -i nrich_latest_amd64.deb",
                "rm nrich_latest_amd64.deb",
        ):
            self.cmd(cmd)

    def install_wpscan(self):
        self.cmd("docker pull wpscanteam/wpscan")

    def install_findomain(self):
        for cmd in (
            "wget https://github.com/findomain/findomain/releases/latest/download/findomain-linux",
            "chmod +x findomain-linux",
            "sudo mv findomain-linux /usr/local/bin"
        ):
            self.cmd(cmd)


    def install(self, name, download, file, binary, tar_gz=False):
        if not exists(f"tools/{name}") or self.update:
            for text, cmd in (
                    (f"Downloading {name}", f"wget {download} --quiet"),
                    ("Extracting tar.gz", f"tar xf {file}") if tar_gz else ("Extracting zip", f"unzip {file}"),
                    (f"Moving {name} to bin", f"sudo mv {binary} /usr/local/bin/{name}") if name != "getau" else (f"Moving {name} to bin", f"sudo mv {binary} /usr/local/bin/getau"),
                    ("Cleanup", f"rm -f {file} README.md LICENSE.md LICENSE"),
                    ("-", f"touch tools/{name}")
            ):
                if text and cmd:
                    self.print("Installer", f"{name} - {text}")
                    self.cmd(cmd)

            if name == "nuclei":
                self.cmd("nuclei -update-templates -update-directory templates")
                self.cmd("nuclei --update")

    def install_ripgen(self):
        for rg_cmd in (
            "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
            "source $HOME/.cargo/env",
            "cargo install ripgen",
        ):
            self.cmd(rg_cmd)

    def install_all_tools(self):

        self.install_nrich()
        # self.install_acunetix()
        self.install_findomain()
        self.install_ripgen()
        self.install_wpscan()

        # for cmd_tool in (
        #         "go get github.com/projectdiscovery/httpx/cmd/httpx@latest",
        #         "go get github.com/projectdiscovery/dnsx/cmd/dnsx@latest",
        #         "go get github.com/projectdiscovery/naabu/v2/cmd/naabu@latest",
        #         "go get github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        #         "go get github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest",
        #         "go get github.com/lc/gau/v2/cmd/gau@latest",
        #         "go get github.com/tomnomnom/unfurl",
        # ):
        #     self.cmd(cmd_tool)
        # sudo ln -s ~/go/bin/httpx /usr/sbin/httpx

        self.install(
            name="httpx",
            download="https://github.com/projectdiscovery/httpx/releases/download/v1.2.0/httpx_1.2.0_linux_amd64.zip",
            file="httpx_1.2.0_linux_amd64.zip",
            binary="httpx"
        )

        self.install(
            name="naabu",
            download="https://github.com/projectdiscovery/naabu/releases/download/v2.0.5/naabu_2.0.5_linux_amd64.zip",
            file="naabu_2.0.5_linux_amd64.zip",
            binary="naabu"
        )

        self.install(
            name="subfinder",
            download="https://github.com/projectdiscovery/subfinder/releases/download/v2.4.9/subfinder_2.4.9_linux_amd64.zip",
            file="subfinder_2.4.9_linux_amd64.zip",
            binary="subfinder"
        )

        self.install(
            name="nuclei",
            download="https://github.com/projectdiscovery/nuclei/releases/download/v2.6.3/nuclei_2.6.3_linux_amd64.zip",
            file="nuclei_2.6.3_linux_amd64.zip",
            binary="nuclei"
        )

        self.install(
            name="dnsx",
            download="https://github.com/projectdiscovery/dnsx/releases/download/v1.0.9/dnsx_1.0.9_linux_amd64.zip",
            file="dnsx_1.0.9_linux_amd64.zip",
            binary="dnsx"
        )

        self.install(
            name="interactsh",
            download="https://github.com/projectdiscovery/interactsh/releases/download/v1.0.1/interactsh-client_1.0.1_Linux_x86_64.zip",
            file="interactsh-client_1.0.1_Linux_x86_64.zip",
            binary="interactsh-client"
        )

        self.install(
            name="getau",
            download="https://github.com/lc/gau/releases/download/v2.0.9/gau_2.0.9_linux_amd64.tar.gz",
            file="gau_2.0.9_linux_amd64.tar.gz",
            binary="gau",
            tar_gz=True
        )

        self.install(
            name="unfurl",
            download="https://github.com/tomnomnom/unfurl/releases/download/v0.2.0/unfurl-linux-amd64-0.2.0.tgz",
            file="unfurl-linux-amd64-0.2.0.tgz",
            binary="unfurl",
            tar_gz=True
        )


def script_init(args) -> str:
    """Create scans folder, workspace and the current scan folder"""

    if not exists("scans"):
        mkdir("scans")

    if not exists("tools"):
        mkdir("tools")

    if not exists(f"scans/{args.domain}"):
        mkdir(f"scans/{args.domain}")

    dir_path = f"scans/{args.domain}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    mkdir(dir_path)

    return dir_path


def main():
    parser = argparse.ArgumentParser(description='HaxUnit')
    parser.add_argument('-d', '--domain', type=str, help='the website to recon: example.com', required=False)
    parser.add_argument('-m', '--mode', type=str, help='you can set to scan `quick` or `extensive`', default='extensive')
    parser.add_argument('-v', '--verbose', type=bool, help='print more information', default=True)
    parser.add_argument('-b', '--bin', type=str, help='set which python bin to use', default='python3')
    parser.add_argument('-is', '--iserver', type=str, help='interactsh server url for self-hosted instance', default='')
    parser.add_argument('-it', '--itoken', type=str, help='authentication token for self-hosted interactsh server', default='')
    parser.add_argument('-acu', '--acunetix', type=str, help='', default='')
    parser.add_argument('-y', '--yes', type=bool, help='yes to all', default=False)
    parser.add_argument('-u', '--update', type=bool, help='update all tools', default=False)
    parser.add_argument('-i', '--install', help='install all tools', default=False, action="store_true")
    parser.add_argument('-r', '--resolvers', help='dnsx - list of resolvers to use (file or comma separated)', default='')
    parser.add_argument('--wpscan-api-token', help='The WPScan API Token to display vulnerability data', default='')

    args = parser.parse_args()
    dir_path = script_init(args)

    hax = HaxUnit(
        site=args.domain,
        mode=args.mode,
        verbose=args.verbose,
        python_bin=args.bin,
        dir_path=dir_path,
        iserver=args.iserver,
        itoken=args.itoken,
        acu_session=args.acunetix,
        yes_to_all=args.yes,
        update=args.update,
        install_all=args.install,
        resolvers_file=args.resolvers,
        wpscan_api_token=args.wpscan_api_token,
    )

    try:
        hax.check_ip()
        hax.sonar_search()
        hax.dnsx_subdomains()
        hax.subfinder()
        hax.gau_unfurl()
        hax.ripgen()
        hax.dnsx_ips()
        hax.sonar_reverse_dns()
        hax.nrich()
        hax.naabu()
        hax.httpx()
        hax.wpscan()
        hax.acunetix()
        hax.nuclei()

        print(f"\ncd {dir_path}\n")
    except KeyboardInterrupt:
        print(f"[{Colors.BOLD}HaxUnit{Colors.RESET}] [{Colors.OK}KeyboardInterrupt{Colors.RESET}] {Colors.WARNING}Aborted{Colors.RESET}")


if __name__ == '__main__':
    main()
