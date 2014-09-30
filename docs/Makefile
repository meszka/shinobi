HTMLS = html/api.html html/redis.html

all: html $(HTMLS)

html:
	mkdir -p html

html/%.html: %.rst
	rst2html $*.rst >html/$*.html

clean:
	rm $(HTMLS)
	rmdir html
