from colorama import init, Fore, Back, Style
init()

import re, requests, json, ast
import constants

articles = []
backup_articles = []

def init():
    """Initiates globals with API data"""
    global articles, backup_articles
    articles = requests.get(constants.API_ARTICLES_ENDPOINT).json()
    with open('wp-articles-backup.txt', 'r') as f:
        backup_users = ast.literal_eval(f.read()).values()  # safer than eval()


def get_title(line):
    if 'Title: ' in line:
        line = line[line.find('Title: ') + len('Title: '):]
    line = line.strip()
    return raw_input(
        (Fore.GREEN + Style.BRIGHT + 'title: ' + Style.RESET_ALL +
         '({}) ').format(line)) or line  # if no user input, defaults to line


def clean_name(name):
    name = name.replace(' - ', '-')
    # remove nickname formatting e.g. "By Ying Zi (Jessy) Mei"
    name = re.sub(r"\([\w\s-]*\)\s", '', name)
    return name


def get_contributors(byline):
    byline = re.sub(r"By:?", '', byline).strip()
    byline = re.findall(r"[\w']+|[.,!-?;]", byline)
    contributors = []
    cutoff = 0
    """Looks through tokens from left to right until a separator is reached,
    then joins the previous tokens into a name. 
    """
    for i in range(0, len(byline)):
        if byline[i] in ',&' or byline[i] == 'and':
            name = clean_name(' '.join(byline[cutoff:i]))
            contributors.append(name)
            cutoff = i + 1
    contributors.append(clean_name(' '.join(
        byline[cutoff:])))  # add last contributor
    contributors = filter(None, contributors)  # removes empty strings
    byline = raw_input(
        (Fore.GREEN + Style.BRIGHT +
         'contributors : ' + Style.RESET_ALL + '({0}) ').format(
             ', '.join(contributors))) or byline  # confirm contributors
    return contributors


def get_summary(line):
    line = re.sub(r"(?i)Focus Sentence:?", '', line).strip()
    return raw_input((Fore.GREEN + Style.BRIGHT + 'summary/focus: ' +
                      Style.RESET_ALL + '({0}) ').format(line)).strip() or line

def manual_article_read(content, message):
    print(Back.RED + Fore.WHITE + Style.BRIGHT + message
          +' You have entered manual article-reading mode for headers. '
          + 'Input "m" to extend the article, input "f" to show the whole '
          + 'article, or press ENTER to continue.' + Style.RESET_ALL + Fore.RED)
    content = content.split('\n')
    lineNum = 0
    while lineNum < len(content):
        print('\n'.join(content[lineNum:lineNum + 5]))
        lineNum += 5
        show_more = raw_input()
        if show_more == 'f':
            print('\n'.join(content[lineNum:]))
        elif show_more != 'm':
            break

# TODO: outquotes

def get_header_end(input):
    HEADER_LINE_PATTERN = re.compile(
        r'(?i)(outquote(\(s\))?s?:)|(focus sentence:)|(word(s)?:?\s\d{2,4})|(\d{2,4}\swords)|article:?'
    )
    return len(input) - next(
        (index for index, value in enumerate(reversed(input))
         if HEADER_LINE_PATTERN.match(value)), -1)

def read_article(text):
    input = text.split('\n')
    input = [line.strip() for line in input]

    data = {}

    data['title'] = get_title(input[0])

    byline = next((line for line in input
                   if line.find('By') >= 0), None)  # defaults to None
    if not byline:
        manual_article_read(text, 'No byline found.')
        byline = raw_input(Fore.GREEN + Style.BRIGHT \
                                 + 'enter contributors separated by ", ": ' \
                                 + Style.RESET_ALL)
    data['contributors'] = get_contributors(byline)

    summary = next((line for line in input
                    if 'focus sentence:' in line.lower()), '')
    if not summary:
        manual_article_read(text, 'No focus sentence found.')
    data['summary'] = get_summary(summary)

    header_end_index = get_header_end(input)
    if header_end_index == -1:
        print(
            Back.RED + Fore.WHITE +
            'No focus sentence or outquote; content could not be isolated. Article skipped.'
            + Back.RESET + Fore.RED)
        return data['title']
    paragraphs = filter(None, input[header_end_index:])
    paragraphs_input = raw_input(
        (Fore.GREEN + Style.BRIGHT +
         'content: ' + Style.RESET_ALL + '({} ... {}) ').format(
             paragraphs[0], paragraphs[-1]))
    if paragraphs_input != '':
        paragraphs = paragraphs_input.split('\n')
    data['content'] = '<p>' + '</p><p>'.join(paragraphs) + '</p>'

    return data


def post_article(data):
    article_response = requests.post(constants.API_ARTICLES_ENDPOINT,
                                    data=json.dumps(data),
                                    headers={'Content-Type': 'application/json'})
    article_response.raise_for_status()
    article = article_response.json()
    global articles
    articles.append(article)
    return article.get('id', -1)