package main

import (
	"crypto/subtle"
	"errors"
	"fmt"
	"io/fs"
	"net"
	"net/http"
	"strconv"
	"strings"
	"syscall"
)

const (
	defaultAddr = "127.0.0.1:8787"
	authEnv     = "WEBDEPLOY_AUTH"
	authRealm   = "itdaapp"
)

func resolveAuth(flagValue, envValue string) string {
	if flagValue != "" {
		return flagValue
	}
	return envValue
}

func newSiteHandler(site fs.FS, auth string) http.Handler {
	return withBasicAuth(http.FileServer(http.FS(site)), auth)
}

func withBasicAuth(next http.Handler, auth string) http.Handler {
	if auth == "" {
		return next
	}

	user, pass, _ := strings.Cut(auth, ":")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestUser, requestPass, ok := r.BasicAuth()
		if !ok || !basicAuthEqual(requestUser, requestPass, user, pass) {
			w.Header().Set("WWW-Authenticate", fmt.Sprintf(`Basic realm="%s"`, authRealm))
			http.Error(w, "401 unauthorized", http.StatusUnauthorized)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func basicAuthEqual(requestUser, requestPass, user, pass string) bool {
	userOK := subtle.ConstantTimeCompare([]byte(requestUser), []byte(user))
	passOK := subtle.ConstantTimeCompare([]byte(requestPass), []byte(pass))
	return userOK&passOK == 1
}

func listenWithFallback(addr string) (net.Listener, string, error) {
	listener, err := net.Listen("tcp", addr)
	if err == nil {
		return listener, listener.Addr().String(), nil
	}
	if !isAddrInUse(err) {
		return nil, "", err
	}

	host, portText, splitErr := net.SplitHostPort(addr)
	if splitErr != nil {
		return nil, "", err
	}

	port, parseErr := strconv.Atoi(portText)
	if parseErr != nil || port < 1 || port >= 65535 {
		return nil, "", err
	}

	for nextPort := port + 1; nextPort <= 65535; nextPort++ {
		candidate := net.JoinHostPort(host, strconv.Itoa(nextPort))
		listener, listenErr := net.Listen("tcp", candidate)
		if listenErr == nil {
			return listener, listener.Addr().String(), nil
		}
		if !isAddrInUse(listenErr) {
			return nil, "", fmt.Errorf("%s 점유로 대체 포트 탐색 중 %s 실패: %w", addr, candidate, listenErr)
		}
	}

	return nil, "", fmt.Errorf("%s 이후 사용 가능한 포트를 찾지 못했습니다", addr)
}

func isAddrInUse(err error) bool {
	if errors.Is(err, syscall.EADDRINUSE) {
		return true
	}

	message := strings.ToLower(err.Error())
	return strings.Contains(message, "address already in use") ||
		strings.Contains(message, "only one usage of each socket address")
}
