//go:build !embed

package main

import (
	"flag"
	"fmt"
	"io/fs"
	"os"
)

type sourceFlags struct {
	dir string
}

func registerSourceFlags(flags *flag.FlagSet) *sourceFlags {
	source := &sourceFlags{}
	flags.StringVar(&source.dir, "dir", ".", "directory to serve")
	return source
}

func (source *sourceFlags) open() (fs.FS, error) {
	info, err := os.Stat(source.dir)
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		return nil, fmt.Errorf("디렉토리가 아님: %s", source.dir)
	}

	return os.DirFS(source.dir), nil
}
