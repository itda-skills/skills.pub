package main

import (
	"bytes"
	"flag"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/fstest"
)

const testMarker = "ITDA-POC-MARKER-7Q2X"

func TestResolveAuth(t *testing.T) {
	tests := []struct {
		name      string
		flagValue string
		envValue  string
		want      string
	}{
		{
			name:      "플래그 값이 env보다 우선한다",
			flagValue: "flag-user:flag-pass",
			envValue:  "env-user:env-pass",
			want:      "flag-user:flag-pass",
		},
		{
			name:      "플래그가 비어 있으면 env를 사용한다",
			flagValue: "",
			envValue:  "env-user:env-pass",
			want:      "env-user:env-pass",
		},
		{
			name:      "둘 다 비어 있으면 빈 값을 반환한다",
			flagValue: "",
			envValue:  "",
			want:      "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := resolveAuth(tt.flagValue, tt.envValue); got != tt.want {
				t.Fatalf("resolveAuth(%q, %q) = %q, want %q", tt.flagValue, tt.envValue, got, tt.want)
			}
		})
	}
}

func TestUsageDoesNotExposeEnvAuth(t *testing.T) {
	t.Setenv(authEnv, "usage-user:usage-pass")

	flags := flag.NewFlagSet("serve", flag.ContinueOnError)
	var output bytes.Buffer
	flags.SetOutput(&output)
	registerServeFlags(flags)
	flags.Usage()

	if usage := output.String(); strings.Contains(usage, "usage-user:usage-pass") {
		t.Fatalf("usage leaked env auth: %q", usage)
	}
}

func TestBasicAuth(t *testing.T) {
	handler := newSiteHandler(fstest.MapFS{
		"index.html": {
			Data: []byte("<!doctype html><p>" + testMarker + "</p>"),
		},
	}, "itda:test-pass")

	t.Run("무인증 요청은 401과 챌린지를 반환한다", func(t *testing.T) {
		response := request(handler, nil)

		if response.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want %d", response.Code, http.StatusUnauthorized)
		}
		if got := response.Header().Get("WWW-Authenticate"); got != `Basic realm="itdaapp"` {
			t.Fatalf("WWW-Authenticate = %q, want %q", got, `Basic realm="itdaapp"`)
		}
	})

	t.Run("올바른 인증은 200과 본문 마커를 반환한다", func(t *testing.T) {
		response := request(handler, func(req *http.Request) {
			req.SetBasicAuth("itda", "test-pass")
		})

		if response.Code != http.StatusOK {
			t.Fatalf("status = %d, want %d", response.Code, http.StatusOK)
		}
		if body := response.Body.String(); !strings.Contains(body, testMarker) {
			t.Fatalf("body = %q, want marker %q", body, testMarker)
		}
	})

	t.Run("잘못된 비밀번호는 401을 반환한다", func(t *testing.T) {
		response := request(handler, func(req *http.Request) {
			req.SetBasicAuth("itda", "wrong")
		})

		if response.Code != http.StatusUnauthorized {
			t.Fatalf("status = %d, want %d", response.Code, http.StatusUnauthorized)
		}
	})
}

func request(handler http.Handler, configure func(*http.Request)) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	if configure != nil {
		configure(req)
	}

	response := httptest.NewRecorder()
	handler.ServeHTTP(response, req)
	return response
}
