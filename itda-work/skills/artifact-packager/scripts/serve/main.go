package main

import (
	"flag"
	"log"
	"net/http"
	"os"
	"time"
)

func main() {
	flags := flag.NewFlagSet("serve", flag.ExitOnError)
	addr, authFlag, source := registerServeFlags(flags)
	flags.Parse(os.Args[1:])

	site, err := source.open()
	if err != nil {
		log.Fatalf("서빙 소스 준비 실패: %v", err)
	}

	listener, actualAddr, err := listenWithFallback(*addr)
	if err != nil {
		log.Fatalf("listen 실패: %v", err)
	}
	defer listener.Close()

	auth := resolveAuth(*authFlag, os.Getenv(authEnv))
	handler := newSiteHandler(site, auth)
	server := &http.Server{
		Handler:           handler,
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       15 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	log.Printf("serving http://%s (auth=%v)", actualAddr, auth != "")
	log.Fatal(server.Serve(listener))
}

func registerServeFlags(flags *flag.FlagSet) (*string, *string, *sourceFlags) {
	addr := flags.String("addr", defaultAddr, "listen address")
	auth := flags.String("auth", "", `basic auth "USER:PASS" (비우면 L0 공개; env WEBDEPLOY_AUTH 지원)`)
	source := registerSourceFlags(flags)
	return addr, auth, source
}
