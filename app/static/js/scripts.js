
//Gera documento excel
function exportTableToExcel(tableID, filename=''){
    var downloadLink;
    var dataType = 'application/vnd.ms-excel';
    var tableSelect = document.getElementById(tableID);
    var tableHTML = tableSelect.outerHTML.replace(/ /g, '%20');

    filename = filename?filename+'.xls':'excel_data.xls';

    // Create download link element
    downloadLink = document.createElement("a");

    document.body.appendChild(downloadLink);

    if(navigator.msSaveOrOpenBlob){
        var blob = new Blob(['\ufeff', tableHTML], {
            type: dataType
        });
        navigator.msSaveOrOpenBlob( blob, filename);
    }else{
        // Create a link to the file
        downloadLink.href = 'data:' + dataType + ', ' + tableHTML;

        // Setting the file name
        downloadLink.download = filename;

        //triggering the function
        downloadLink.click();
    }
}

function armazenarConsulta(){
    var placa = document.getElementById("placa").value;
    var dt_incial = document.getElementById("data_inicial").value;
    var dt_final = document.getElementById("data_final").value;
    localStorage.setItem("placa", placa);
    localStorage.setItem("dt_inicial", dt_incial);
    localStorage.setItem("dt_final", dt_final);
	console.log("armazenado com sucesso...")
}

function ultimaConsulta(){
	if (localStorage.length == 0){
		console.log("Sem valores...")
	}
	else {
		var ultima_placa = localStorage.getItem("placa")
		var ultima_data_inical = localStorage.getItem("dt_inicial")
		var ultima_data_final = localStorage.getItem("dt_final")
		document.getElementById("placa").value = ultima_placa;
		document.getElementById("data_inicial").value = ultima_data_inical;
		document.getElementById("data_final").value = ultima_data_final;
	}
}

function verificar_data(){
            var dt_inicial = document.getElementById("data_inicial").value
            var dt_final = document.getElementById("data_final").value
            if (dt_final < dt_inicial){
                alert("Data Final nÃ£o pode ser menor que a Data Inicial...")
                document.getElementById("gerar_relatorio").disabled = true
            }else {
                document.getElementById("gerar_relatorio").disabled = false
            }
}