customasm = customasm.exe 


all: main.asm
	$(customasm) main.asm -o main.bin
	@echo "Done"

logisim: main.asm
	$(customasm) main.asm -o main.bin -f logisim8
	@echo "Done"