//go:build embed

package main

import (
	"embed"
	"flag"
	"io/fs"
)

//go:embed all:web
var siteFS embed.FS

type sourceFlags struct{}

func registerSourceFlags(_ *flag.FlagSet) *sourceFlags {
	return &sourceFlags{}
}

func (*sourceFlags) open() (fs.FS, error) {
	return fs.Sub(siteFS, "web")
}
