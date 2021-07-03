from nmigen_boards.ulx3s import ULX3S_85F_Platform

from src.maximum_pooling import MaximumPooling


if __name__ == "__main__":
    ULX3S_85F_Platform().build(MaximumPooling(2), do_program=False)
