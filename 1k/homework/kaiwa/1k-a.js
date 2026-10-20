// 大問題１
var answerFirstArr = ["1#ba4","2#jie3","3#ge1","4#gui4","5#shu1","6#yi2","7#me4i","8#di4","9#gu1","10#nu2"];
// 大問題２
var answerSecondArr = ["1#B","2#B","3#A","4#B","5#B"];
// 大問題3
var answerThirdArr = ["1#D","2#B","3#A","4#C","5#A@A"];
// 大問題4
var answerFourthArr = ["1#姓@叫@私の苗字は山田で、山田愛子と言います。","2#老师@先生、なんとおっしゃいますか。",
　　　　　　　　　　　　　　"3#中文@山田愛子は中国語を勉強しています。","4#请坐@ようこそ、おかけください。","5#不客气@ありがとうございます。どういたしまして。"];
// 大問題5
var answerFifthArr = ["1#我是爱知淑德大学的学生。","2#老师，您贵姓？","3#我姓张，叫张华。","4#欢迎欢迎，请坐。","5#谢谢，不客气。"];
// 大問題6
var answerSixthArr = ["1#B","2#D","3#C","4#A","5#C"];
// 問題配列　,の後に貼り付け
var answerArray = [answerFirstArr, answerSecondArr, answerThirdArr, answerFourthArr, answerFifthArr, answerSixthArr];


// 点数1
// var pointFirstArr = ["1#4","2#2","3#1","4#1","5#1","6#1","7#1","8#1","9#1","10#1"];
// 問題配列　,の後に貼り付け
// 
// 提出された問題
// var point_arr_string = new Array();
// 
// CSVファイルパス
//var CSVFilePath = "F:/dokai/homework/csv/homeworkfile.csv";

// ファイル入力流
//var fso=new ActiveXObject("Scripting.FileSystemObject");
//以写的方式打开文件
//var ForWriting=2;
//打开文件并从文件末尾开始写
//var ForAppending=8;
//var f;

// num1:大問題No, num2: 少問題No　動くな
function doFindAnswer(num1, num2) {
    // 答え
    var result="";
    // 大問題No
    if (num1 > 0) {
      if (answerArray.length >= num1) {
        // 大問題を取得
        var firstLeveArray = answerArray[num1 - 1];
        
        // 小問題配列空判断
        if (firstLeveArray.length > 0) {
          // 小問題配列を繰り返す
          for (var i = 0; i < firstLeveArray.length; i++) {
            // 小問題回答文字
            var answers = firstLeveArray[i];
            // 問題Noを判断
            var noAndString = answers.split("#");
            if (noAndString.length < 2) {
              return;
            }
            
            // 問題Noを比較
            if (noAndString[0] == num2) {
              result = noAndString[1];
              break;;
            }
          }
        }
      }
    }
    
    // 答えを戻す
    return result;
};

// num1:大問題No, num2: 少問題No　動くな
function doFindPoint(num1, num2) {
    // 点数
    var point = 0;
    // 大問題No
      if (pointSumArray.length >= num1) {
        // 大問題を取得
        var firstLeveArray = pointSumArray[num1 - 1];
        
        // 小問題配列空判断
        if (firstLeveArray.length >= num2) {
            // 小問題回答文字
            var answers = firstLeveArray[num2 - 1];
            // 問題Noを判断
            var noAndString = answers.split("#");
            if (noAndString.length < 2) {
              return point;
            }
            // 問題点数を返す
            point = noAndString[1];
        }
      }
    
    // 答えを戻す
    return point;
};

// num1:大問題No, num2: 少問題No　動くな
function doCheckHaved(num1, num2, pointArrayStr) {
  // 結果 初期値該当問題なし
  var resule = false;
  // 問題Indexを計算
  var queIndex = 0;
  // 回答済み問題の数値
  var pointArr = pointArrayStr.split('a')
  var answeredCnt = pointArr.length - 1;
  // 大問題数を数え
  var firstLevelCount = answerArray.length;
  // 大問題NUM-1が0以下の場合、処理抜け
  if ((num1 - 1) < 0) {
    return;
  }
  // 大問題１の場合
  if (num1 = 1) {
    // 該当問題のindexを設定
    queIndex = num2;
    
    if (queIndex <= answeredCnt) {
      resule = true;
    }
  }
  // 大問題２以上の場合
  if (num1 > 1)  {
    // 問題配列をループ
    for (var i = 0; i < pointFirstArr.length; i++) {
      // 大問題数値を判断
      if (i < (num1 -1)) {
        // indexを加算
        queIndex = queIndex + answerArray[i].length;
      } else {
        break;
      }
    }
    
    // 該当大問題の小問題数値を加算
    queIndex = queIndex + num2;
    
    if (queIndex <= answeredCnt) {
      resule = true;
    }
  }
  
  // 結果を返す
  return resule;
};


function putAnswer(resultStr) {
    point_arr_string.push(resultStr);
}

function gerResultStr() {
  alert(point_arr_string);
  return point_arr_string;
}
//将内容写到指定路径
//function writeFile(content,filePath){
//var timestamp = new Date();·
//alert(timestamp);
//    alert(content);
//    alert(filePath);
//    f=fso.OpenTextFile(filePath,ForAppending,true);
//    f.WriteLine(content);
//    f.close();
//};

