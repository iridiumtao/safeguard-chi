all: \
	index.md \
	1_create_server.ipynb \
	2_launch_containers.ipynb \
	3_student_exercise_1.ipynb \
	4_student_exercise_2.ipynb \
	5_benchmark.ipynb \
	6_delete.ipynb

clean:
	rm -f index.md 1_create_server.ipynb 2_launch_containers.ipynb 3_student_exercise_1.ipynb 4_student_exercise_2.ipynb 5_benchmark.ipynb 6_delete.ipynb

index.md: snippets/create_server.md snippets/launch_containers.md snippets/student_exercise_1.md snippets/student_exercise_2.md snippets/benchmark.md snippets/delete.md snippets/footer.md
	cat snippets/create_server.md snippets/launch_containers.md snippets/student_exercise_1.md snippets/student_exercise_2.md snippets/benchmark.md snippets/delete.md snippets/footer.md > index.tmp.md
	grep -v '^:::' index.tmp.md > index.md
	rm index.tmp.md

1_create_server.ipynb: snippets/create_server.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/create_server.md \
		-o 1_create_server.ipynb
	sed -i 's/attachment://g' 1_create_server.ipynb

2_launch_containers.ipynb: snippets/launch_containers.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/launch_containers.md \
		-o 2_launch_containers.ipynb
	sed -i 's/attachment://g' 2_launch_containers.ipynb

3_student_exercise_1.ipynb: snippets/student_exercise_1.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/student_exercise_1.md \
		-o 3_student_exercise_1.ipynb
	sed -i 's/attachment://g' 3_student_exercise_1.ipynb

4_student_exercise_2.ipynb: snippets/student_exercise_2.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/student_exercise_2.md \
		-o 4_student_exercise_2.ipynb
	sed -i 's/attachment://g' 4_student_exercise_2.ipynb

5_benchmark.ipynb: snippets/benchmark.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/benchmark.md \
		-o 5_benchmark.ipynb
	sed -i 's/attachment://g' 5_benchmark.ipynb

6_delete.ipynb: snippets/delete.md
	pandoc --resource-path=../ --embed-resources --standalone --wrap=none \
		-i snippets/frontmatter_python.md snippets/delete.md \
		-o 6_delete.ipynb
	sed -i 's/attachment://g' 6_delete.ipynb
