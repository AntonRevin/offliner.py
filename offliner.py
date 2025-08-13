import click
import os, sys
import requests
from fake_useragent import UserAgent
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, urljoin
from enum import Enum
import hashlib

class errors(Enum):
    """
    Standard error messages
    """
    def __init__(self, err, msg):
        self.err = err
        self.msg = msg
    
    INVALID_OUTPUT_DIR          = "00", "Output directory is not a valid path"
    TARGET_DIR_EXISTS           = "01", "Target directory already exists"
    INVALID_URL                 = "02", "Failed to access the target url"
    ERROR_LOADING_PAGE          = "03", "Failed to access the target url"
    ERROR_LOADING_PAGE_SELENIUM = "04", "Failed to access the target url"
    ERROR_SAVING_RESOURCE       = "05", "Failed to download a static resource"

def fail(error) -> None:
    """
    Displays a standard error message and exits
    """
    click.secho(F"ERROR {error.err}: ", fg="red", nl=False)
    click.echo(error.msg)
    exit()

def fetch_and_parse_page(target: str, use_selenium: bool) -> tuple[BeautifulSoup, requests.Session]:
    """
    Downloads a target page using the selected method
    """
    soup = BeautifulSoup()
    if use_selenium: 
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By

            options = Options()
            options.add_argument("--headless")
            driver = webdriver.Chrome(options=options)
            driver.get(target)
            return BeautifulSoup(driver.page_source, "lxml"), session
        except:
            fail(errors.ERROR_LOADING_PAGE_SELENIUM)
    else:
        try:
            session = requests.Session()
            header = {"User-Agent": str(UserAgent.chrome)}
            response = session.get(target)
            if response.ok:
                return BeautifulSoup(response.text, "lxml"), session
            else:
                fail(errors.ERROR_LOADING_PAGE)
        except:
            fail(errors.ERROR_LOADING_PAGE)

def get_url_hash(dirty_url: str) -> tuple[str, str]:
    """
    Hashes a provided url
    """
    # remove leading and trailing slashes
    clean_url = dirty_url.strip("/")
    # return hash
    g = hashlib.sha1()
    g.update(clean_url.encode())
    return g.hexdigest(), clean_url

def get_local_path(base_netloc: str, base_url_ind: int, target_dir: str, page: str, extension: str) -> str:
    """
    Converts a url to a local path
    """
    # determine the relative local path to establish
    local_path = page[base_url_ind:]
    if "\\" in target_dir: local_path = local_path.replace("/", "\\")
    # remove leading and trailing slashes
    if "\\" in target_dir:
        local_path = local_path.strip("\\")
    else:
        local_path = local_path.strip("/")

    # determine the directory to place this file in
    local_dir_path = os.path.join(target_dir, os.path.dirname(local_path))
    # remove leading and trailing slashes
    if "\\" in target_dir:
        local_dir_path = local_dir_path.strip("\\")
    else:
        local_dir_path = local_dir_path.strip("/")
    if not os.path.isdir(local_dir_path): os.makedirs(local_dir_path)

    file_name = os.path.basename(local_path)
    if len(file_name) == 0: file_name = "index"
    return os.path.join(local_dir_path, file_name + extension)

def save_resources(soup: BeautifulSoup, resources: dict[str, str], dir: str, session: requests.Session, url: str, tag: str, inner: str) -> None:
    """
    Searches for, and downloads relevant (de-duplicated) static resources
    """
    for instance in soup.find_all(tag):
        if instance.has_attr(inner):
            try:
                _, extension = os.path.splitext(os.path.basename(instance[inner]))
                url_hash, _ = get_url_hash(instance[inner])
                file_url = urljoin(url, instance.get(inner))
                filename = url_hash + extension
                instance[inner] = os.path.join(dir, filename)
                if not url_hash in resources.keys(): # this resource has not been downloaded yet
                    filepath = os.path.join(dir, filename)
                    if not os.path.isfile(filepath):
                        with open(filepath, 'wb') as file:
                            resource = session.get(file_url)
                            file.write(resource.content)
                    resources[url_hash] = file_url
            except:
                fail(errors.ERROR_SAVING_RESOURCE)

@click.command()
@click.option("--target", "target", help="Base target url", type=str, required=True)
@click.option("--depth", "depth", help="Max search depth", type=int, default=1, show_default=True)
@click.option("--just-this", "just_this", help="Only download the target page (sets depth to 0)", is_flag=True, show_default=True)
@click.option("--output-dir", "output_dir", help="Location to store the offline page(s)", type=str, required=True)
@click.option("--use-browser", "use_selenium", help="Spawn a browser instance to render pages (for websites that render using javascript). Note that this is much slower", type=bool, default=False, show_default=True)
def offliner(target, depth, just_this, output_dir, use_selenium) -> None:
    """
    Tool for downloading an offline version of webpages.
    """
    # preamble and checks
    if just_this:
        depth = 0

    if not os.path.isdir(output_dir) or os.path.isfile(output_dir):
        fail(errors.INVALID_OUTPUT_DIR)

    # Sanity check before execution
    click.echo()
    click.secho("⚙️  offliner.py", fg="yellow", bold=True)
    click.echo("You are about to download the site ", nl=False)
    click.secho(target, fg="green", nl=False)
    click.echo(" using a depth of", nl=False)
    click.secho(F" [{depth}]", fg="green", nl=False)
    click.echo(" to ", nl=False)
    click.secho(output_dir, fg="green")
    click.echo()
    click.confirm("Would you like to proceed?")

    # Parse the base page data
    soup, session = fetch_and_parse_page(target, use_selenium)

    # Determine target pages
    target_pages_to_download = {get_url_hash(target): target}
    base_netloc = urlsplit(target).netloc
    base_url_ind = target.find(base_netloc) + len(base_netloc)
    base_url = target[:base_url_ind]
    click.echo()

    # Setup the local folders
    target_dir = os.path.join(output_dir, base_netloc)
    static_dir = os.path.join(target_dir, "static")
    if os.path.isdir(target_dir):
        fail(errors.TARGET_DIR_EXISTS)
    else:
        os.mkdir(target_dir)
    if not os.path.isdir(static_dir): os.mkdir(static_dir)
    resource_types = {"img": "src", "link": "href", "script": "src"}
    resources = {}

    if depth > 0:
        for l in soup.find_all("a"):
            if l.has_attr("href"):
                netloc = urlsplit(l["href"]).netloc
                if len(netloc) == 0 or netloc == base_netloc:
                    dirty_url = l["href"]
                    if len(netloc) == 0: dirty_url = urljoin(target, l["href"])
                    url_hash, clean_url = get_url_hash(dirty_url)
                    target_pages_to_download[url_hash] = clean_url
        click.echo("Found ", nl=False)
        click.secho(len(target_pages_to_download), fg="yellow", nl=False)
        click.echo(" pages to download")
    else:
        click.echo("Just downloading ", nl=False)
        click.secho("one", fg="yellow", nl=False)
        click.echo(" page")

    # pre-populate all local paths
    local_paths = {}
    for hash, page in target_pages_to_download.items():
        local_paths[page] = get_local_path(base_netloc, base_url_ind, target_dir, page, ".html")

    # Download files
    click.echo()
    downloaded_files = 0
    with click.progressbar(
        length=len(target_pages_to_download),
        label="Fetching",
        item_show_func=lambda a: a,
        show_pos=True
    ) as bar:
        downloaded_files = 0
        for hash, page in target_pages_to_download.items():
            # if we're not running the base page, we need to fetch the new one
            if downloaded_files > 0: 
                soup, session = fetch_and_parse_page(page, use_selenium)
            # download any static resources
            for tag, inner in resource_types.items():
                save_resources(soup, resources, static_dir, session, target, tag, inner)
            # update all internal links
            for l in soup.find_all("a"):
                if l.has_attr("href"):
                    netloc = urlsplit(l["href"]).netloc
                    if len(netloc) == 0 or netloc == base_netloc:
                        url_to_check = l["href"].lower().strip("/")
                        if len(netloc) == 0:
                            url_to_check = urljoin(base_url, l["href"]).strip("/")
                        if url_to_check in local_paths.keys():
                            l["href"] = local_paths[url_to_check]
                        else: 
                            l["href"] = "BROKEN"
            with open(local_paths[page], "wb") as file:
                file.write(soup.prettify('utf-8'))
            downloaded_files += 1
            bar.update(1, page)

    # done!
    click.echo()
    click.secho("Done!", fg="green")
    click.echo("Downloaded ", nl=False)
    click.secho(downloaded_files, fg="yellow", nl=False)
    click.echo(" pages and ", nl=False)
    click.secho(len(resources), fg="yellow", nl=False)
    click.echo(" static files to ", nl=False)
    click.secho(target_dir, fg="yellow")

# main
if __name__ == "__main__":
    offliner()