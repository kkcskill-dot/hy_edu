# e-book 메모 동기화 — nginx 설정 (한 번만)

e-book 서재(`reader.html`)의 형광펜·밑줄·메모는 기본으로 **그 기기에 저장**됩니다.
nginx 서버에 아래 저장 공간을 만들면 **아이폰·아이패드가 같은 메모를 공유**합니다(GitHub Pages 주소에서는 동기화되지 않고 기기에만 저장).

동작 방식: 서재 → `🔄 기기 간 동기화`에서 아이디·비밀번호 입력 → 책마다 `annot/<책>.json` 파일을 읽고(GET) 합쳐서 저장(PUT)합니다.

## 지금 서버(http://13.209.76.33/, 사이트가 주소 맨 앞 `/`)에 그대로 쓰는 순서

```bash
# 1) WebDAV 모듈 확인 — with-http_dav_module 이 출력되어야 함
nginx -V 2>&1 | grep -o with-http_dav_module

# 2) 메모 저장 폴더(웹 루트 밖) + 동기화 아이디·비밀번호
sudo mkdir -p /var/lib/hyedu-annot
sudo chown www-data:www-data /var/lib/hyedu-annot      # nginx 실행 계정이 nginx 이면 nginx:nginx
sudo htpasswd -c /etc/nginx/.htpasswd-hyedu 원하는아이디   # 없으면: sudo apt install apache2-utils
```

사이트 `server { … }` 블록 안에 추가:

```nginx
location /annot/ {
    alias /var/lib/hyedu-annot/;
    dav_methods PUT DELETE;
    create_full_put_path on;
    dav_access user:rw;
    client_max_body_size 5m;
    autoindex off;
    auth_basic "hyedu notes";
    auth_basic_user_file /etc/nginx/.htpasswd-hyedu;
    add_header Cache-Control "no-store" always;
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
# 확인: 201/204 → 다시 읽으면 {"items":{}}
curl -u 아이디:비밀번호 -X PUT --data '{"items":{}}' http://13.209.76.33/annot/_check.json
curl -u 아이디:비밀번호 http://13.209.76.33/annot/_check.json
```

그다음 아이폰·아이패드에서 `e-book 서재 → 🔄 기기 간 동기화`에 같은 아이디·비밀번호를 넣으면 됩니다.

> ⚠️ 지금 주소는 http(암호화 없음)라 동기화 비밀번호가 네트워크에서 보일 수 있습니다. 다른 곳에 쓰지 않는 비밀번호를 쓰고,
> 가능하면 도메인을 연결해 HTTPS(예: Let's Encrypt)로 바꾸세요.

---

아래는 사이트가 `https://도메인/hy_edu/` 같은 하위 경로에 있을 때의 일반 설명입니다.

## 1. 준비 (서버에서)

```bash
# WebDAV 모듈 포함 여부 확인 (출력에 with-http_dav_module 이 보여야 함)
nginx -V 2>&1 | grep -o with-http_dav_module

# 메모 저장 폴더 — 배포(git pull/rsync)로 지워지지 않도록 웹 루트 밖에 둡니다
sudo mkdir -p /var/lib/hyedu-annot
sudo chown www-data:www-data /var/lib/hyedu-annot     # nginx 실행 계정에 맞게 (예: nginx)

# 동기화용 아이디·비밀번호 (apache2-utils 의 htpasswd)
sudo htpasswd -c /etc/nginx/.htpasswd-hyedu 원하는아이디
```

## 2. nginx 설정 (사이트 server 블록 안)

사이트가 `https://도메인/hy_edu/` 경로에 있으면 그대로, 도메인 루트(`/`)에 있으면 `location /annot/` 로 바꾸세요.

```nginx
location /hy_edu/annot/ {
    alias /var/lib/hyedu-annot/;
    dav_methods PUT DELETE;
    create_full_put_path on;
    dav_access user:rw;
    client_max_body_size 5m;
    autoindex off;

    auth_basic "hyedu notes";
    auth_basic_user_file /etc/nginx/.htpasswd-hyedu;
    add_header Cache-Control "no-store" always;
}

# (선택) 문서·버전 파일은 항상 최신 확인 — 없어도 자동 갱신은 동작합니다
location ~* ^/hy_edu/.*\.(html|md|json)$ {
    add_header Cache-Control "no-cache";
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## 3. 확인

```bash
curl -u 아이디:비밀번호 -X PUT --data '{"items":{}}' https://도메인/hy_edu/annot/_check.json   # 201 또는 204
curl -u 아이디:비밀번호 https://도메인/hy_edu/annot/_check.json                               # {"items":{}}
```

- 비밀번호가 전송되므로 **HTTPS 주소**에서 사용하세요.
- 백업: 서재의 `⬇️ 메모 백업` 버튼으로 언제든 파일로 내려받을 수 있습니다. 서버 쪽은 `/var/lib/hyedu-annot/` 폴더를 보관하면 됩니다.
