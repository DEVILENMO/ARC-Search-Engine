def extract_urls(file_path):
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line.startswith('//') and line.startswith('http'):
                urls.append(line)
    return urls


if __name__ == '__main__':
    file_path = 'crawler_starting_site.txt'
    extracted_urls = extract_urls(file_path)
    print(f"提取到{len(extracted_urls)}个网址:")

    print(','.join(extracted_urls))
