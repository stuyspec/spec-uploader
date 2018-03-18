package main

import (
	"github.com/stuyspec/uploader/log"
	"github.com/stuyspec/uploader/driveclient"
	"github.com/stuyspec/uploader/graphql"
	"github.com/stuyspec/uploader/parser"

	"bufio"
	"google.golang.org/api/drive/v3"
	"os"
	"strings"
)

// UploadArticle uploads an article of an issue of a volume via its ID.
func UploadArticle(
	fileID string,
	volume, issue int,
	photos, art []*drive.File,
) {
	rawText := driveclient.DownloadGoogleDoc(fileID)
	articleAttrs, missingAttrs := parser.ArticleAttributes(rawText)
	if len(missingAttrs) > 0 {
		log.Errorf(
			"Unable to parse article with id %s; missing attributes %v.\n",
			fileID,
			missingAttrs,
		)
		return
	}
	PrintArticleInfo(articleAttrs)
	articleAttrs["volume"] = volume
	articleAttrs["issue"] = issue

	for {
		uploadConfig := Input("upload? (y/n/r/o): ")
		if uploadConfig == "y" {
			// [YES]: Upload article
			break
		} else if uploadConfig == "n" {
			// [NO]: Skip article
			log.Println() // aesthetic line break between articles
			return
		} else if uploadConfig == "r" {
			// [RELOAD]: Article content changed, download again
			log.Println()
			UploadArticle(fileID, volume, issue, photos, art)
			return
		} else if uploadConfig == "o" {
			// [OPEN]: Open Drive file in browser (often used before RELOAD for
			// fixing article content).
			OpenDriveFileManual(fileID, "document")
		} else {
			log.Errorf("[%s] is not a valid option.\n", uploadConfig)
		}
	}

	article, err := graphql.CreateArticle(articleAttrs)
	if err != nil {
		log.Errorf("Unable to create article with id %s. %v\n", fileID,	err)

		// If there is an error, reload the article. It could be solved by a simple
		// open -> edit -> reload. If not, then it can be skipped.
		log.Println()
		UploadArticle(fileID, volume, issue, photos, art)
		return
	} else {
		log.Noticef("Created Article #%s.\n", article.ID)
	}

	CreateArticleMedia(article, photos, art)

	log.Println()
}

// CreateArticleMedia lets the user choose which media accompanies an article.
func CreateArticleMedia(article graphql.Article, photos, art []*drive.File) {
	for {
		if mediaConfig := Input("add media? (y/n): "); mediaConfig == "y" {
			// [YES]: Upload media
			break
		} else if mediaConfig == "n" {
			// [NO]: Skip article
			return
		}
	}

	for {
		log.Info("==========")
		mediaAttrs := map[string]string{
			"articleID": article.ID,
		}
		filename := Input("-> filename: ")
		if filename == "" {
			return
		}
		for _, p := range photos {
			if p.Name == filename {
				mediaAttrs["webContentLink"] = p.WebContentLink
			}
		}
		if _, found := mediaAttrs["mediaType"]; !found {
			// No matching photo found, let's check art...
			for _, a := range art {
				if a.Name == filename {
					mediaAttrs["mediaType"] = "illustration"
					mediaAttrs["webContentLink"] = a.WebContentLink
				}
			}
		}
		if _, found := mediaAttrs["mediaType"]; !found {
			log.Errorf("Unable to find media with name %s.\n", filename)
			continue
		}
		mediaAttrs["title"] = Input("-> title: ")
		mediaAttrs["caption"] = Input("-> caption: ")
		for {
			if artistName := Input("-> artist: "); artistName != "" {
				mediaAttrs["artistName"] = artistName
				break
			}
		}
		medium, err := graphql.CreateMedium(mediaAttrs)
		if err != nil {
			log.Errorf("Unable to create media. %v\n",	err)
			continue
		} else {
			log.Noticef("Created Medium #%s.\n", medium.ID)
		}
	}
}

// PrintArticleInfo prints article attributes, usually to prevent mistakes.
func PrintArticleInfo(attrs map[string]interface{}) {
	log.Headerf("%v\n", attrs["title"])
	log.Infof("contributors: ")
	var contributors string
	for i, nameVars := range attrs["contributors"].([][]string) {
		if i > 0 {
			contributors += ", "
		}
		contributors += strings.Join(nameVars, " ")
	}
	log.Printf("%s\n", contributors)

	log.Infof("summary: ")
	log.Printf("%v\n", attrs["summary"])

	log.Infof("content: ")
	truncatedContent := attrs["content"].(string)
	if words := strings.Split(truncatedContent, " "); len(words) > 20 {
		truncatedContent = strings.Join(words[:20], " ") + "..."
	}
	log.Printf("%s\n", truncatedContent)
}

// Input lets the user respond to a prompt. It returns the user's response.
// If there were a scanning error, it returns an empty string.
func Input(prompt string) string {
	reader := bufio.NewReader(os.Stdin)
	log.Infof(prompt)
	text, err := reader.ReadString('\n')
	if err != nil {
		log.Fatalf("Unable to read response. %v\n", err)
	}
	return strings.Trim(text, "\n")
}