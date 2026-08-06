#先布置环境
from __future__ import annotations

import json
import math
import os
import re
import threading
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import limit
import pdfplumber

#然后告诉系统我在哪一个地方
ROOT = Path(__file__).resolve().parent
#Path(__file__)是只当前app.py文件所在的位置
#resolve()函数是获取该位置
#.parent也是一个函数，是指得到某地址的父地址
#该行代码是为了方便定义后续地址
Data_location = ROOT / "data"#定位数据库的地址
#因为这个智能客服需要一个user interface所以要在本地网页中设计一个页面
#设计这个页面需要定义该页面的端口号和IP地址


#接下来我要用好长一段文字解释下面的代码

#1.环境变量：这关乎于程序的一个特点：只有在运行时才会分配内存。一旦关闭程序中所有的变量就会销毁
#  但是有一些变量储存的值是通用的，意思是每次都需要用，就比如说我这个程序设置的网页接口，他应当是一
#  个恒定的值。那么像这种值就算是环境变量
#  通常环境变量会储存在一个名字叫.env的文件中


from dotenv import load_dotenv
load_dotenv(".env")
#2.这个函数的功能就是：从名字叫.env的文件中读取环境变量，放到执行python程序的控制台中
#  注意这个函数原有的需要的参数是这些load_dotenv("文件名字.env")。
#  该方程的具有默认参数，如果你不传参数的话它默认是load_dotenv(".env")
#  这也是为什么他会自动找名字为.env的文件的原因


HOST = os.getenv("RAG_HOST", "127.0.0.1")
#3.这行代码中涉及的函数需要跟上面那个函数一块使用
#  load_dotenv从.env文件读取环境变量放置在控制台中
#  该函数从控制台中取参数
#  os.getenv("想获得的环境变量的名字","控制台中没有该环境变量时，设置的默认值")


PORT = int(os.getenv("RAG_POST", "7000"))
#这里又包含了另三个知识：
#   1.IP地址是一个字符串
#   2.端口号是一个int数据
#   3.python想转换数据类型只需要在外层包一个他的数据类型。如int则用 int()。













#下面的部分是用来处理读取过后的文本

#第一个任务将读取过后的文本的信息进行净化和优化，方便后续信息的识别和存储
def clean_informantion (value:str) -> str: #str在python中是字符串的意思
# 这里设计python中函数的书写：我用和C++对应的方式解释
#  1.函数开头标明的返回数据的类型，换到了括号后用 -> 数据类型表示
#  2.python中函数开头只需要带一个def就可以了
#  3.python中填参数的时候，不需要写参数的类型，但是建议像这个地方一样写一下备注:str


    value = value.replace("\x00", " ")
#这个是python中的字符串自带的函数函数形式为：
#字符串.replace(旧的字符串, 新的字符串)


    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub("\n{3,}", "\n\n", value)
#字符串自带replace()函数确实能用，但不够强大。所以就用到了 re.sub()函数
#这个函数需要穿的参数如下：
#re.sub(正则表达式，新的字符串，函数操作的对象)
#正则函数的规律如下
#正则运算式子：https://share.mubu.com/doc/2SD8I3sIyPG



    return value.strip()
#这一行的作用有 两个
#   1.一方面返回数据
#   2.另一方面字符串自带的strip函数可以消除字符串开头和结尾自带的换行符和空格符



#第三个任务：将字符串切割成一个一个token
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*|\d+(?:\.\d+)?|[\u4e00-\u9fff]")
#这一行同样涉及到了正则运算
#首先re.compile()函数是在正则字串翻译成一串规则后将这串规则存贮下来，这样以后就无需再重复翻译该
#正则字串

#其次该正则字串涉及到的元字符
#1. []   表示其中任意一个字符
#2. -    用在中间时表示从...至...
#        如果用在开头或末尾则直接表示-字符
#3. *    表示前面在到达|或开头的所有字符串总共出现了0次或大于等于2次
#4. |    表示”或“， 用于分割和拆分。
#5. \d   表示0到9任意的数字
#6. +    表示前面在到达|或开头的所有字符串总共出现了大于等于1次
#7. (?:) 表示将括号内的多个字符当成一个字符
#8. \    如果\后跟一个元字符则表示元字符所代表的那个符号而不是元字符产生的作用
#9. ?    表示前面的字符串重复出现1或0次
#在这个解释下这串正则运算可以这样翻译
#一整个字符串被分割，分割方法有三种
#第一种  发现 以字母作为开头的 ”字母，数字，-与_的结合“，则分割一下
#第二种  发现 所有的形式为 《n个数字 “+或不+” . “+” n个数字形式》的字符串，则分割一下
#其实意思就是所有的整数或者小数
#第三种  发现 汉字的集合，则分割一下

#TOKEN_RE接收并储存了这个正则分割规则，并成为了一个特殊的变量
#这个变量有一个自带的函数 findall(字符串),返回值是一个集合
#例如这里我可以 TOKEN_RE.findall(value)


#这时就可以引入这个新的方程了
def tokens(value:str) -> list[str]:
    return [item.lower() for item in TOKEN_RE.findall(value)]

#这个地方涉及到了个知识点

#1.python钟创建数组的方式
#      变量名 = [所有的元素]
#2.也因为这个创建数组的方式，方便了动态数组的设置
#      比如这里我无法确认TOKEN_RE.findall(value)返回的数组的size，并且二他还是个变量
#      所以这里就可以在[]内部使用for循环方便
#3.最后是python中字符串自带的一个功能
#      lower()函数，可将字符串内所有字母转化成小写


#下面写的这个函数是用在比较搜索的那一块的

ALIASES = {
    "软件工程": "software engineering",
    "软件过程": "software process lifecycle waterfall agile scrum",
    "需求工程": "requirements engineering elicitation specification validation",
    "需求": "requirement requirements",
    "功能需求": "functional requirement",
    "功能性需求": "functional requirement",
    "非功能需求": "nonfunctional requirement quality attributes",
    "非功能性需求": "nonfunctional requirement quality attributes",
    "软件设计": "software design architecture component interface",
    "架构": "architecture architectural design",
    "耦合": "coupling",
    "内聚": "cohesion",
    "软件测试": "software testing test",
    "黑盒测试": "black box testing",
    "白盒测试": "white box testing",
    "单元测试": "unit testing",
    "集成测试": "integration testing",
    "系统测试": "system testing",
    "验收测试": "acceptance testing",
    "回归测试": "regression testing",
    "软件管理": "software management project management",
    "项目管理": "project management planning scheduling estimation",
    "风险": "risk risk management",
    "敏捷": "agile",
    "瀑布": "waterfall",
    "维护": "maintenance software evolution",
    "质量": "quality software quality assurance",
}

def Translate(value:str)-> list[str]:
    temp = value
    for chinese, english in sorted(ALIASES.items(), key=lambda item:item[0], reverse=True):
        if chinese in value:
            temp += " " + english
    return tokens(temp)
#这个函数的知识点：
#   1. python内自带的sorted函数。 sorted函数的形式
#      sorted(被排序集合, key=排序依靠的元素的性质, reverse=是否倒序)
#   2. lambda简单定义函数的方法。平常的”def 函数名(参数)->返回值类型“形式的定义函数的方法有时候太过于麻烦
#      所以就有了lambda这种方法，这种方法定义函数的形式如下
#      lambda 参数: 返回值
#   3. python内自带的字典
#      这个跟C++中的域名很像，主要的用法是 “将一个值转化成另一个值的过程” 包装成一个函数方便后续的书写
#      这个字典的大概形式是：
#      字典名字 = {
#          A = B
#          D = E
#          F = G
#      }
#      发挥作用的例子：
#      字典名字[A]
#      这个时候他就会返回B
#   4. 字典函数自带的子函数：
#      items()  会返回一个数组，这个数组中的元素是：“一个大小为二的数组”
#               这个地方需要注意item()的返回值不是一个“二维数组”，而是一个“嵌套数组”
#   5. keys()   例如这个例子中会返回[A, D, F]
#      value()  例如这个例子中会返回[B, E, G]

@dataclass
class Chunk:
    chunk_id: int
    source: str
    page:int
    text: str
    title: str
#知识点：
#   @dataclass这是在设置类的时候的一个简便方式，系统可以自动帮你补全构造函数
#   python本身设置类的时候是不会将类包含的成员变量专门列出来，通常都是直接从构造函数
#   中直接接收。但是这个@dataclass是个特殊的，它刚好和python自带的反过来了，它不需要设置
#   构造函数，只把需要的成员变量列出来








#下面这个类的作用是：依靠前面写的函数去实现：
#   1. 读取PDF
#   2. 将读取的数据变成数据库

class LocalIndex:
    #第一个知识点就是函数的初始化
    #这一部分我需要的成员变量都有
    #   1. 资料数据存储的位置路径
    #   2. 后续需要用的用来存储词频的counter数组
           #一个是用来储存每个片段的词频，另一个用来储存总的词频
    #   3. 一个用来储存被加工过的切片的数组
    #   4. 一个用来存映射的字典符数组

    def __init__(self, data_path:Path):
        #注意：
        #在这个函数中带self的被定义的变量是成员变量，其他函数可以直接使用
        self.document_data: list[dict[str, Any]] = []#一个字典集，用于存贮每个pdf的标题，名字还有页码
        self.data_path = data_path
        self.chunks: list[Chunk] = []
        self.total_frequency: Counter[str] = Counter()#注意这个counter需要大写，要不然系统识别不出来他是个计数器
        self.single_frequency: list[Counter[str]] = []
        self.average_length = 1.0

    #下面这个函数的知识点很多，我会先在文中标注，然后在后文解释
    def split_page(self,text:str)->list[str]:
        #最终返回的数组
        pieces:list[str] = []
        #将原字符串加工成一个数组
        paragraphs = [temp.strip() for temp in re.split(text) if temp.strip]#知识点一
        a_container_used_for_save_classified_str = " "
        for paragraph in paragraphs:
            if paragraph + a_container_used_for_save_classified_str + 2 <= 1500:
                a_container_used_for_save_classified_str = f"{a_container_used_for_save_classified_str}\n\n{paragraph}"#知识点四
            else:
                if a_container_used_for_save_classified_str:
                    pieces.append(a_container_used_for_save_classified_str)#知识点二
                current = paragraph
        return pieces or [text[:1500]]#知识点三
    #知识点一：设立数组时的快速方式
    #        [a.strip() for a in b if a.strip()]
    #        参数解释：
    #        a: 需要加入到数组中的元素,从b中取出的元素
    #        b: 数组，a的来源
    #        strip(): 一个函数用来去除字符串开头和结尾的某个字符
    #        例如:
    #        strip("a")  就可以删掉开头和结尾的a字符
    #        执行顺序:
    #        for a in b:
    #           if a.strip()
    #               [].append(a.strip)
    #知识点二：数组的append()函数
    #        例如数组 b
    #        b.append(a)
    #        就是指在b这个数组的末尾加上a这个元素
    #        特殊情况解释：
    #        如果a是个数组，那么b会变成一个二维数组
    #知识点三：python自带的切分函数
    #        可以用作字符串取子集
    #        例如:字符串A
    #        A[0:8:1]
    #        字符串[start: end: step]
    #        这个意思就是： 在A这个字符串中从0开始每次往后走一步到达8为止。取所有经过的字节
    #        如果A是数组的话就是
    #        在A这个数组中从0开始每次往后走一步，走到8位置
    #知识点四：合并字符串的简便方法：
    #        假如a的内容是huy      b的内容是oiu
    #        f"{字符串a}hgiugyi{字符串b}“
    #        则最终返回的字符串是：”huyhgiugyioiu“


    def extract_and_process(self)->None:
        chunks: list[Chunk] = []
        document_data: list[dict[str, Any]] = []
        chunk_Id: int = 0#这个不可以写到for循环内，防止一些切片的id重复
        for each_pdf_path in sorted(self.data_path.glob("*.pdf")):#知识点一：路径变量的glob函数，可以寻找该路径下所有名字与括号内相似的文件
            with pdfplumber.open(each_pdf_path) as pdf_content:#知识点二：python的打开pdf的函数    知识点三：python的with功能
                total_pages = len(pdf_content.pages)#每个pdf的属性，之后需要存到document_data这个数组中
                for page_number, each_page in enumerate(pdf_content.pages,start = 1):#知识点四：pdf数据的内置变量page #知识点五： enumerate函数
                    cleaned_content = clean_informantion(each_page.extract_text())#知识点六： page变量的extract_text()函数
                    if cleaned_content:
                        for each_piece in self.split_page(cleaned_content):
                            chunks.append(Chunk(
                                chunk_id = chunk_Id,
                                source = each_pdf_path.name,
                                page = page_number,
                                text = each_piece,
                                title = each_pdf_path.stem#知识点七：path数据类型的stem函数
                                )
                            )
                            chunk_Id += 1
            document_data.append({"name":each_pdf_path.name, "title":each_pdf_path.stem, "pages":total_pages})
        self.chunks = chunks
        self.document_data = document_data
        single_frequency: list[Counter[str]] = []
        total_frequency: Counter[str] = Counter()
        for each_chunk in chunks:
            temp_tokens = tokens(each_chunk.text)
            single_frequency.append(Counter(temp_tokens))
            total_frequency.update(Counter(temp_tokens).keys())#知识点八：Counter数据类型的keys()函数
        self.single_frequency = single_frequency
        self.total_frequency = total_frequency
        self.average_length = sum(sum(fre.values()) for fre in single_frequency) / max(len(self.single_frequency), 1)
    #知识点一: 路径变量的glob函数：
    #        路径A.glob("*adada*")
    #        例如上面这个例子
    #        他会返回路径A下，名字中所有带adada的文件
    #        *号代表有或者没有字符
    #        路径A.glob("*adada")
    #        上面这个例子会返回所有名字后缀为adada的文件
    #知识点二: python打开pdf的函数     pdfplumber.open(pdf路径) as pdf数据类型名字
    #        注意点：该函数返回的是一个《pdf数据类型》
    #知识点三: 经常与文件操作同时出现的一种语法
    #        它给打开pdf函数进行了简单的加缀
    #        with pdfplumber.open(pdf路径) as pdf数据类型名字
    #        它的好处是可以自主帮你关闭pdf
    #知识点四: pdf的内置数据类型pages
    #        它是一个数组，不是一个单纯的变量
    #        pdf数据类型.pages
    #知识点五: enumerate函数，用于遍历的函数
    #        enumerate(需要遍历的数组, start = 第一个索引数)
    #        他会返回两个变量：1.索引数+1
    #                      2.被遍历的数组中的元素
    #        例子: enumerate([1, 2, 3], start = 5)
    #        返回值: {5，1}，{6，2}，{7，3}
    #知识点六: page数据类型extract.text()
    #        会返回一个字符串。通常用于提取每一页的文字
    #知识点七: path数据类型的三种函数
    #        1. path.name   纯文件名 + 后缀名
    #        2. path.stem   纯文件名
    #        3. path.suffix 后缀名字
    #知识点八: Counter数据类型的keys()函数
    #        Counter.keys()
    #        返回Counter中所有的只要出现过一次的字节
    #        并且只返回一次


    def search(self, question: str)->list[dict[str, Any]]:
        processed_question = Translate(question)
        if not processed_question:
            return []
        question_words_frequency = Counter(processed_question)
        total_docs = len(self.chunks)
        scored: list[tuple[float, Chunk]] = []#知识点一
        k1 = 1.5
        b = 0.75
        for chunk, chunk_term_frequency in zip(self.chunks, self.single_frequency):#知识点二    知识点三
            length = max(sum(chunk_term_frequency.values()), 1)
            score = 0.0
            for term, each_question_word_frequency in question_words_frequency.items():
                each_chunk_term_frequency = chunk_term_frequency.get(term, 0)
                if not each_chunk_term_frequency:
                    continue
                term_frequency_appearing_in_different_document =self.total_frequency.get(term, 0)
                idf = math.log(1 + (total_docs - term_frequency_appearing_in_different_document + 0.5) / (term_frequency_appearing_in_different_document + 0.5))
                score += idf *((each_chunk_term_frequency * (k1 + 1)) / (term_frequency_appearing_in_different_document + k1 * (1 - b + b * length / self.average_length)))
                if each_question_word_frequency > 1:
                    score *= 1 + min(each_chunk_term_frequency - 1, 2) * 0.08
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)#知识点四
        return[#这串代码需要着重解释一下
            {"rank": index, "score": round(score, 4), **asdict(chunk)}
            for index, (score, chunk) in enumerate(scored[:limit], start=1)
        ]
    #知识点一: tuple数组数据类型，类似c++中的固定数组，大小不可以改变，不可以使用append
    #知识点二: zip函数
    #        通常与for循环一块使用
    #        作用是可以一次性取多个数据
    #        例子：
    #        for a, b in zip(传a的数据, 传b的数据):
    #知识点三: 从字典符数据类型中取数据
    #        大致有两种取法 例子：字典符数组A
    #        1.直接取
    #        for a in A     这个时候只需要用一个变量去承接就好
    #        2.调用函数取
    #        for a, b in A.item() 如果想将key和values都取出来就用item，第一个是key，第二个是values
    #        易错点，如果是从字典符数组中取，取出来的是一个字典符
    #知识点四: 两种不同的sort函数
    #        1. 直接调用的
    #        sorted(被排序数组, key = 排序依据, reverse = true排序顺序)
    #        2. 后缀使用
    #        数组名.sort(key = 排序依据, reverse = true排序顺序)
    #        这种调用方式会自动从数组中取元素，然后排序，再放回去


    def source_list(self)->list[dict[str, Any]]:
        return self.document_data


INDEX = LocalIndex(Data_location)

def generate_prompt(question: str, information: list[dict[str, Any]]) -> str:
    content = "\n\n".join(f"[资料{index}]  文件: {each.get('source')} 页码: {each.get('page')} \n内容: {each.get('text')} " for each, index in enumerate(information, start = 1))#知识点一
    content = content[:5000].rsplit("\n", 1)[0]
    return f"""
    你是一个智能客服，你的名字叫做南宫羽。请使用下方资料回答用户问题。

要求：
1. 只根据资料回答，不要臆测；
2. 用简洁、清晰的中文回答；必要时保留英文术语。
3. 在相关句子末尾添加引用，格式为 [资料 1]，引用必须来自下方资料编号。
4. 如果问题是学习概念，请先给结论，再给要点或例子。
5. 涉及到知识点的语句不要带任何语气
6. 回答完知识点后，用可爱的语气卖个萌
7. 资料不足时明确说资料中没有足够信息，并用可爱的，猫娘的语气道歉，
8. 仅在不涉及到知识点的语句中，对用户的称谓改成老大，‘你’改成‘泥’。比如：”你还有什么问题吗“改成”老大，泥还有什么问题吗？“
9. 卖萌时用颜文字辅助
用户问题：{question}

资料：
{content}
"""
#知识点一:字符串内置的函数join()
#       这个不是用来操作调用它的字符串对象的，而是将调用它的字符串对象插入到括号里的可迭代对象里的
#       字符串a.join(可迭代字符串对象b)
#       例子:
#       a = "aaaa"
#       b = a.join(b for b in["o", "p", "q"])
#       print(b)
#       最后得到的结果是:
#       oaaaapaaaaq
#知识点二:三个双引号的作用
#       正常来说赋值字符串只能写单行
#       加三引号后就可以多行输入了

def call_openai(prompt:str, information:list[dict[str, Any]])->tuple[str | None, str | None]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    address = os.getenv("OPENAI_API_URL", "").rstrip("/") + "/chat/completions"
    if not api_key:
        return None, "QAQ老大，泥还没给窝装脑子呢喵-^—。"
    if not address:
        return None, "*_*老大，窝找不到泥给窝配的脑子在哪里 (^._.^) "
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": "You answer based only on supplied course materials."},
            {"role": "user", "content": generate_prompt(prompt, information)},
        ],
    }
    request = urllib.request.Request(address, data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip(), None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return None, f"模型请求被拒绝（HTTP {exc.code}）。请检查 API 地址、模型名和密钥。{detail}"
    except urllib.error.URLError as exc:
        return None, f"无法连接模型服务：{exc.reason}。请检查网络或 OPENAI_BASE_URL。"
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        return None, f"模型返回格式异常：{exc}。"
    except TimeoutError:
        return None, "模型请求超时，请稍后重试。"



def answer_question_collection(question: str):
    information = INDEX.search(question)
    answer = call_openai(question, information)
    if not answer[0]:
        return answer[1]
    return answer[0]
class Handler(BaseHTTPRequestHandler):#这个是python中继承父类的方法，BaseHTTPRequestHandler是python自带的处理网页的请求的类，可以帮助处理一些底层细节
    def _send(self, status: int, payload: Any, content_type: str = "application/json; charset=utf-8") -> None:
        body = payload if isinstance(payload, bytes) else (payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        #上面这条的的理解顺序要从后往前看
        #先判断payload是不是bytes
        #   如果是就直接返回bytes
        #   如果不是就判断payload是不是字符串
        #       如果是字符串就对字符串加密
        #           然后返回该结果
        #       如果不是就将Payload转换成json数据
        #           然后再加密，再返回该结果

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        #上面这四条都是说明函数，向浏览器说明发送的信息的消息
        self.end_headers()
        self.wfile.write(body)#这条代码是真正传消息的信息

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":#当浏览器想访问某个路径上的文件是，它会指定一个路径，python程序会自动将这个路径保存到path这个成员变量中
            self._send(HTTPStatus.OK, HTML, "text/html; charset=utf-8")
        elif self.path.startswith("/assets/"):#elif是else is的简写
            asset_name = self.path.removeprefix("/assets/")#通常来讲照片等静态资源会存放在一个叫assets的文件夹里面
            #而这两个字符串内置的函数
            #   startswith("a")是用来检测某个字符串是否是以"a"开头的
            #   removeprefix("a")是用来去除某个字符串开头的字符串的
            asset_path = (ROOT / "assets" / asset_name).resolve()
            assets_root = (ROOT / "assets").resolve()#这个resolve函数不是必须存在的，它可以帮忙规范路径对象的格式
            #上面三行的逻辑是
            #   1. 路径后面跟着的就是特定文件的名字
            #   2. 因为path对象通常都是相对路径，没有办法用系统去识别，所以要将其转化成绝对路径
            if asset_path.parent != assets_root or not asset_path.is_file():#is_file()函数是用来确认该路径是否的确指向了一个真实的文件
                self._send(HTTPStatus.NOT_FOUND, {"error": "Asset not found"})
                return
            mime = "image/png" if asset_path.suffix.lower() == ".png" else "application/octet-stream"
            self._send(HTTPStatus.OK, asset_path.read_bytes(), mime)
        elif self.path == "/api/health":
            self._send(HTTPStatus.OK, {
                "ok": True,
                "chunks": len(INDEX.chunks),
                "documents": len(INDEX.document_data),
                "model_configured": bool(os.getenv("OPENAI_API_KEY", "").strip()),
                "model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            })
        elif self.path == "/api/sources":
            self._send(HTTPStatus.OK, {"sources": INDEX.source_list()})
        else:
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/chat":
            self._send(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            question = str(body.get("message", "")).strip()
            if not question:
                raise ValueError("message is required")
            result = answer_question_collection(question, int(body.get("top_k", 5)))
            self._send(HTTPStatus.OK, result)
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "请输入有效的问题。"})
        except Exception as exc:  # keep the API response readable for local debugging
            self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"处理失败：{exc}"})

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


def main() -> None:
    print(f"Loading PDFs from {Data_location} ...")
    INDEX.extract_and_process()
    print(f"Indexed {len(INDEX.document_data)} documents into {len(INDEX.chunks)} chunks.")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"RAG customer service is running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()


























