# offliner.py
A simple script for downloading a local copy of websites, including static assets, for offline use.

I was looking for an easy way to keep a local copy of the [odin docs](https://pkg.odin-lang.org/) ahead of a long train-ride (thank you, Deutche Bahn Wifi and terrible cell service) but found that other solutions downloaded way too much content, were overly complicated for such a simple use-case, or had poor configurability.

## Installation
1. Create and activate a [python virtual environment](https://docs.python.org/3/library/venv.html) in the same folder as the repo
    - *This step is optional, but highly recommended*
2. Install the dependencies using your choice of package manager, for example, pip
```console
pip install -r requirements.txt
```
3. Check that everything is working
```console
python offliner.py --help
```

# Usage
## Basic use-case:
1. Provide a target url (using `--target` or `-t`) and local folder (using `--output-dir` or `-out`) to download the content to:
```console
python offliner.py -t https://pkg.odin-lang.org/core/ --out C:\Users\user\Downloads\sites
```
2. The programme will ask you to confirm the provided settings, confirm with `y`.

> By default a max search depth of 1 is assumed, meaning that the script will scrape the target page, plus all pages on the same domain that the target points to (using standard `<a>` html tags). You can select a different depth using `--depth` or `-d`.

This will create a new folder `C:\Users\user\Downloads\sites\pkg.odin-lang.org` with the downloaded html files in the same logical folder structure as implied by the urls, alongisde a static folder with js, css, and image files (hashed to avoid collisions such as `style.css`).

## For sites rendered using javascript
For websites using client-side rendering (i.e., if the base case doesn't seem to work), you can use the option `--use-browser`. This will launch a headless browser (using selenium) to render the page as if it were viewed by chrome, and then function normally. 
> Note, using this option will be **MUCH SLOWER**, so only use it if the basic case does not work.

## Full set of options
### Required arguments
|Argument|Alternative|Description|
|---|---|---|
|`--target`|`-t`|Base target URL|
|`--output-dir`|`-out`|Location to store downloaded files|

### Optional arguments
|Argument|Alternative|Description|Example usage|
|---|---|---|---|
|`--just-this`|`-this`|Downloads only the provided target page (sets depth to 0)|   |
|`--depth`|`-d`|Lets you select the target depth to use when scraping, provide an integer ≥ 0|`--depth 2`|
|`--use-browser`|`-b`|Use a headless browser to visit sites instead of a basic get, useful for sites that render using client-side javascript (I'm looking at you, `<noscript>`). Note that using this option will be **MUCH SLOWER**|   |
|`--help`||Displays usage information|`python offliner.py --help`|

## Planned features
In no particular order;
- Multiple target mode
- Wizzard mode (walk-through)
- Target filtering